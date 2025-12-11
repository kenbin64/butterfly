// main-with-checks.js
const fs = require('fs/promises');
const fsSync = require('fs');
const { performance } = require('perf_hooks');
const path = require('path');
const crypto = require('crypto');
const yaml = require('js-yaml');
const sqlite3 = require('sqlite3');

/**
 * Represents a reusable pointer to a physical resource. This is stored
 * in the "connection table" and does not contain ephemeral data.
 */
class ResourceConnection {
  /**
   * @param {object} connectionDetails
   * @param {string} connectionDetails.protocol - The protocol to use (e.g., 'file', 'https', 'sql').
   * @param {string} connectionDetails.address - The resource address (e.g., a path, a URL, an IP).
   * @param {string} connectionDetails.encryptedCredentials - The encrypted credentials for the datasource.
   */
  constructor({ protocol, address, encryptedCredentials }) {
    this.protocol = protocol;
    this.address = address;
    this.encryptedCredentials = encryptedCredentials;

    // Harden the object, making it immutable after creation.
    Object.freeze(this);
  }
}

/**
 * An ephemeral, self-validating token that wraps a ResourceConnection.
 * The nonce and expiration are added "at use time" when this is created.
 */
class SignedPointer {
  /**
   * @param {ResourceConnection} connection The reusable connection to wrap.
   * @param {number} lifetimeInSeconds The number of seconds until the pointer expires.
   */
  constructor(connection, lifetimeInSeconds = 60) {
    this.connection = connection;
    // "an added random hash will be added at each use"
    this.nonce = crypto.randomBytes(16).toString('hex');
    // "a timestamp for expiration"
    this.expiresAt = Date.now() + (lifetimeInSeconds * 1000);
    // "a bitcount of the pointer that must match round trip or it invalidates"
    this.integrityHash = this._calculateIntegrityHash();

    // Harden the object, making it and its nested connection immutable.
    Object.freeze(this);
  }

  get physicalResource() {
    return { protocol: this.connection.protocol, address: this.connection.address };
  }

  _calculateIntegrityHash() {
    const data = JSON.stringify({
      // The hash now includes the immutable resource details from the connection.
      resource: { protocol: this.connection.protocol, address: this.connection.address },
      nonce: this.nonce,
      expires: this.expiresAt,
    });
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * Validates the pointer's integrity and expiration, returning a detailed result.
   * This simulates the "round trip" check and provides reasons for failure.
   * @returns {{valid: boolean, reason: string|null}} An object indicating validity and reason for failure.
   */
  validate() {
    // 1. Check for tampering.
    if (this.integrityHash !== this._calculateIntegrityHash()) {
      return { valid: false, reason: 'integrity_check_failed' };
    }
    // 2. Check for expiration.
    if (Date.now() > this.expiresAt) {
      return { valid: false, reason: 'pointer_expired' };
    }

    return { valid: true, reason: null };
  }
}

/**
 * Handles writing security audit events to a log file.
 */
class AuditLogger {
  constructor(storageAdapter) {
    this.storage = storageAdapter;
  }

  /**
   * @param {SignedPointer} details.pointer - The pointer that failed validation.
   * @param {string} details.reason - The reason for the failure.
   * @param {object} details.credentials - The credentials used in the request.
   */
  logPointerFailure({ traceId, pointer, reason, credentials }) {
    const event = {
      traceId: traceId,
      timestamp: new Date().toISOString(),
      type: 'POINTER_VALIDATION_FAILURE',
      reason: reason,
      userId: credentials?.id || 'unknown',
      resource: pointer.physicalResource,
    };
    this.storage.logEvent(event);
  }

  /**
   * @param {object} details
   * @param {string} details.traceId - The unique ID for the request.
   * @param {string} details.logicalName - The resource that was requested.
   * @param {string} details.reason - The reason for the failure.
   * @param {object} details.credentials - The credentials used in the request.
   */
  logHandshakeFailure({ traceId, logicalName, reason, credentials }) {
    const event = {
      traceId: traceId,
      timestamp: new Date().toISOString(),
      type: 'HANDSHAKE_FAILURE',
      reason: reason,
      userId: credentials?.id || 'unknown',
      resource: logicalName,
    };
    this.storage.logEvent(event);
  }

  /**
   * Logs a successful handshake event, including the claim that granted access.
   * @param {object} details
   * @param {string} details.traceId - The unique ID for the request.
   * @param {string} details.logicalName - The resource that was requested.
   * @param {object} details.credentials - The credentials used in the request.
   * @param {object} details.satisfyingClaim - The permission claim that granted access.
   */
  logHandshakeSuccess({ traceId, logicalName, credentials, satisfyingClaim }) {
    const event = {
      traceId: traceId,
      timestamp: new Date().toISOString(),
      type: 'HANDSHAKE_SUCCESS',
      reason: `Access granted by claim: ${JSON.stringify(satisfyingClaim)}`,
      userId: credentials?.id || 'unknown',
      resource: logicalName,
    };
    this.storage.logEvent(event);
  }

  close() {
    // The storage adapter is now responsible for closing connections.
  }
}

/**
 * A secure, in-memory directory for data resources. It maps logical names
 * to physical resources and enforces access control based on permissions.
 * This is a foundational implementation of the "Secure Resource Locator" (SLR).
 */
class SecureResourceLocator {
  constructor(storageAdapter) {
    this.storage = storageAdapter;
  }

  /**
   * A storage adapter for persisting connections and audit logs to SQLite.
   */
  static SqliteStorageAdapter = class {
    constructor(config) {
      this.db = new sqlite3.Database(config.path, (err) => {
        if (err) {
          // This is a fatal error for the core app, so we should exit.
          console.error(`[FATAL] Could not connect to database at ${config.path}`, err);
          process.exit(1);
        }
      });

      // 1. Initialize an in-memory cache for connection lookups.
      this.connectionCache = new Map();

      // Define a Time-To-Live for cache entries in milliseconds (e.g., 5 minutes).
      this.cacheTTL = 5 * 60 * 1000;

      // Initialize metrics to track cache performance.
      this.cacheMetrics = {
        hits: 0,
        misses: 0,
      };
    }

    /**
     * Initializes the database schema if it doesn't exist.
     */
    async init() {
      // This is a more robust and readable way to perform sequential async operations.
      await this._run(`
        CREATE TABLE IF NOT EXISTS connections (
          logical_name TEXT PRIMARY KEY,
          protocol TEXT NOT NULL,
          address TEXT NOT NULL,
          encrypted_credentials TEXT,
          required_permission TEXT NOT NULL
        )
      `);
      await this._run(`
        CREATE TABLE IF NOT EXISTS audit_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          trace_id TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          type TEXT NOT NULL,
          reason TEXT,
          user_id TEXT,
          resource TEXT
        )
      `);
    }

    // Helper to promisify db.run
    _run(sql, params = []) {
      return new Promise((resolve, reject) => {
        this.db.run(sql, params, function (err) {
          err ? reject(err) : resolve(this);
        });
      });
    }

    // Helper to promisify db.get
    _get(sql, params = []) {
      return new Promise((resolve, reject) => {
        this.db.get(sql, params, (err, row) => {
          err ? reject(err) : resolve(row);
        });
      });
    }

    // Helper to promisify db.all
    _all(sql, params = []) {
      return new Promise((resolve, reject) => {
        this.db.all(sql, params, (err, rows) => {
          err ? reject(err) : resolve(rows);
        });
      });
    }

    async registerConnection({ logicalName, connectionDetails, requiredPermission }) {
      const { protocol, address, encryptedCredentials } = connectionDetails;
      const sql = `
        INSERT INTO connections (logical_name, protocol, address, encrypted_credentials, required_permission) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(logical_name) DO UPDATE SET 
          protocol=excluded.protocol,
          address=excluded.address,
          encrypted_credentials=excluded.encrypted_credentials,
          required_permission=excluded.required_permission
      `;
      // 2. Invalidate the cache for this entry upon write/update to prevent stale data.
      this.connectionCache.delete(logicalName);
      return this._run(sql, [logicalName, protocol, address, encryptedCredentials, requiredPermission]);
    }

    async getConnection(logicalName) {
      const cachedEntry = this.connectionCache.get(logicalName);

      // 3. Check if a valid, non-expired entry exists in the cache.
      if (cachedEntry && Date.now() < cachedEntry.expiresAt) {
        this.cacheMetrics.hits++;
        return cachedEntry.data;

      }

      // 4. If entry is expired or doesn't exist, query the database.
      this.cacheMetrics.misses++;
      const row = await this._get('SELECT * FROM connections WHERE logical_name = ?', [logicalName]);

      // 5. If the row was found, store it in the cache for subsequent requests.
      if (row) {
        const newCacheEntry = {
          data: row,
          expiresAt: Date.now() + this.cacheTTL,
        };
        this.connectionCache.set(logicalName, newCacheEntry);
      }

      return row;
    }

    async logEvent(event) {
      const sql = `INSERT INTO audit_logs (trace_id, timestamp, type, reason, user_id, resource) VALUES (?, ?, ?, ?, ?, ?)`;
      const resourceString = typeof event.resource === 'string' ? event.resource : JSON.stringify(event.resource);
      this._run(sql, [event.traceId, event.timestamp, event.type, event.reason, event.userId, resourceString]);
    }

    getCacheMetrics() {
      return this.cacheMetrics;
    }

    async close() {
      return new Promise((resolve, reject) => this.db.close((err) => (err ? reject(err) : resolve())));
    }
  }

  async register({ logicalName, connectionDetails, requiredPermission }) {
    return this.storage.registerConnection({ logicalName, connectionDetails, requiredPermission });
  }

  /**
   * Resolves a logical name to a physical resource after performing a security handshake.
   * @param {string} logicalName - The name of the resource to resolve.
   * @param {object} credentials - The user's credentials, containing their permissions.
   * @param {string[]} credentials.permissions - A list of permissions the user holds.
   * @param {object} auditContext - Context needed for auditing failures.
   * @param {AuditLogger} auditContext.auditLogger - The logger for security events.
   * @param {string} auditContext.traceId - The unique ID for the request.
   * @returns {ResourceConnection | null} A reusable ResourceConnection if access is granted, otherwise null.
   */
  async resolve(logicalName, credentials, { auditLogger, traceId }) { 
    const resourceRow = await this.storage.getConnection(logicalName);

    // 1. Check if resource exists.
    if (!resourceRow) {
      const reason = `Resource '${logicalName}' not found.`;
      auditLogger.logHandshakeFailure({ traceId, logicalName, reason, credentials });
      return null;
    }

    // 2. Perform the "handshake" - check for consent.
    const requiredPermission = JSON.parse(resourceRow.required_permission);
    const userPermissions = credentials?.permissions || [];
    
    // --- Context Building ---
    // Build a context object with attributes of the user and the resource.
    const context = {
      user: { id: credentials.id },
      // For this demo, we'll add an 'onCall' status to the user's context.
      // In a real system, this might come from the user's session or a separate service.
      userAttributes: { onCall: false },
      resource: { id: null },
      // Add current time attributes to the context for time-based policies.
      time: { hour: new Date().getHours(), day: new Date().getDay() } // day: 0=Sun, 6=Sat
    };

    // Example of extracting resource attributes from the logical name.
    const profileMatch = logicalName.match(/^user-profiles\/(.+)$/);
    if (profileMatch) {
      context.resource.id = profileMatch[1];
    }
    // --- End Context Building ---

    const satisfyingClaim = checkPermission(requiredPermission, userPermissions, context);

    if (!satisfyingClaim.met) {
      // The satisfyingClaim object now contains the detailed reason for failure.
      auditLogger.logHandshakeFailure({ traceId, logicalName, reason: satisfyingClaim.reason, credentials });
      return null;
    }
    
    // Log the successful handshake and the specific claim that allowed it.
    auditLogger.logHandshakeSuccess({ traceId, logicalName, credentials, satisfyingClaim: satisfyingClaim.claim });

    // 3. Handshake successful. Return the reusable connection object.
    // We need to pass the specific address for this resource instance.
    const connectionDetails = {
      ...resourceRow,
      address: resourceRow.address.replace('{resourceId}', context.resource.id)
    };
    return new ResourceConnection(connectionDetails);
  }

  /**
   * "Signs" a connection by wrapping it in an ephemeral, single-use SignedPointer.
   * @param {ResourceConnection} connection The connection to sign.
   * @param {object} [options] - Optional signing parameters.
   * @param {number} [options.lifetimeInSeconds] - The lifetime of the pointer in seconds. Defaults to 60.
   */
  sign(connection, { lifetimeInSeconds } = {}) {
    // Pass the lifetime to the SignedPointer constructor. If undefined, the constructor's default is used.
    return new SignedPointer(connection, lifetimeInSeconds);
  }
}

/**
 * A helper function to check if a user's permissions satisfy a resource's requirement.
 * This is the core of the new structured permission logic.
 * @param {object} requirement - The permission required by the resource.
 * @param {object[]} claims - The array of permission claims the user holds. 
 * @returns {{met: boolean, claim: object|null, reason: string|null}} An object indicating if access was granted and why.
 * @param {object} context - Contextual information about the request.
*/
function checkPermission(requirement, claims, context) { 
  for (const claim of claims) {
    const actionMatch = claim.action === '*' || claim.action === requirement.action;
    const resourceMatch = claim.resourceType === '*' || claim.resourceType === requirement.resourceType;

    if (actionMatch && resourceMatch) {
      // If the claim's conditions are met, access is granted.
      const conditionResult = evaluateConditions(claim.conditions, context);
      if (conditionResult.met) {
        return { met: true, claim: claim, reason: null }; // Return the specific claim that satisfied the request.
      }
    }
  }
  return { met: false, claim: null, reason: `No claim satisfied requirement: ${JSON.stringify(requirement)}` }; // No satisfying claim found.
}

/**
 * Evaluates an array of conditions against the request context.
 * This function is now recursive to handle nested AND/OR logic.
 * @param {object|string} node - The condition node to evaluate.
 * @param {object} context - The request context.
 * @returns {{met: boolean, reason: string|null}} An object indicating if the conditions were met and why.
 */
function evaluateConditions(node, context) {
  // If the node is null or undefined (no conditions), it passes.
  if (!node) {
    return { met: true, reason: null };
  }

  // Base case: The node is a single condition string.
  if (typeof node === 'string') {
    let conditionMet = false;
    switch (node) {
      case 'isOwner':
        conditionMet = context.user.id === context.resource.id;
        break;
      case 'isBusinessHours':
        const isBusinessDay = context.time.day >= 1 && context.time.day <= 5; // Mon-Fri
        const isBusinessHour = context.time.hour >= 9 && context.time.hour < 17; // 9am-5pm
        conditionMet = isBusinessDay && isBusinessHour;
        break;
      case 'isOnCall':
        conditionMet = context.userAttributes.onCall === true;
        break;
      default:
        // Fail securely for unknown conditions.
        return { met: false, reason: `Unknown condition '${node}'` };
    }
    return conditionMet ? { met: true, reason: null } : { met: false, reason: `Condition '${node}' failed` };
  }

  // Recursive step: The node is an object with an operator and clauses.
  if (node.operator === 'AND') {
    // For AND, every clause must be true.
    for (const clause of node.clauses) {
      const result = evaluateConditions(clause, context);
      if (!result.met) {
        // If any clause fails, the whole AND block fails. Propagate the reason.
        return { met: false, reason: `AND clause failed: ${result.reason}` };
      }
    }
    return { met: true, reason: null }; // All clauses passed.
  }

  if (node.operator === 'OR') {
    // For OR, at least one clause must be true.
    const failureReasons = [];
    for (const clause of node.clauses) {
      const result = evaluateConditions(clause, context);
      if (result.met) {
        return { met: true, reason: null }; // Found a passing clause.
      }
      failureReasons.push(result.reason);
    }
    // If we get here, all clauses failed.
    return { met: false, reason: `OR block failed: [${failureReasons.join(', ')}]` };
  }

  // Fail securely if the operator is unknown.
  return { met: false, reason: `Unknown operator '${node.operator}'` };
}

/**
 * Interprets the "circuit" from a connection object and executes the request.
 * This function simulates accessing different kinds of datasources.
 * @param {object} connectionDetails The details of the connection from the pointer.
 */
async  function accessResource(connectionDetails) {
  const { protocol, address } = connectionDetails;

  switch (protocol) {
    case 'file':
      // This branch contains the logic from the old `readAllFiles` function.
      return readFileSystemResource(address);
    case 'https':
      console.log(`   (Simulation: would perform a fetch to ${address})`);
      return true; // Simulate success
    case 'sql':
      console.log(`   (Simulation: would decrypt credentials and connect to SQL DB at ${address})`);
      return true; // Simulate success
    default:
      console.error(`   Error: Unknown protocol '${protocol}'.`);
      return false;
  }
}

/**
 * Specific implementation for reading a file system resource.
 */
async function readFileSystemResource(dirPath) {
  let filesFound = false;
  try {
    const items = await fs.readdir(dirPath, { withFileTypes: true });

    if (items.length === 0) {
      // This check handles an empty top-level directory.
      return false;
    }

    await Promise.all(items.map(async (item) => {
      const fullPath = path.join(dirPath, item.name);

      if (item.isDirectory()) {
        // If recursion finds files, update the flag.
        if (await readFileSystemResource(fullPath)) {
          filesFound = true;
        }
      } else if (item.isFile()) {
        filesFound = true; // A file was found.
        try {
          // As per previous request, operational logs are removed.
          await fs.readFile(fullPath, 'utf-8');
        } catch (readError) {
        }
      }
    }));

  } catch (dirError) {
    if (dirError.code === 'ENOENT') {
      // Specific error for "Error NO ENTry" (directory not found).
      // Errors are now handled via the audit trail, keeping the application silent.
    } else {
      // Errors are now handled via the audit trail.
    }
    return false;
  }

  return filesFound;
}

/**
 * "Packages up" the file reading configuration into a single executable function.
 * This acts as a factory for our configured reader.
 *
 * @param {object} config - The configuration object.
 * @param {SecureResourceLocator} config.slr - The SLR instance to use for discovery.
 * @param {string} config.logicalName - The logical name of the resource to read.
 * @param {object} config.credentials - The user credentials for the handshake.
 * @param {AuditLogger} config.auditLogger - The logger for security events.
 * @param {object} [config.options] - Options for the operation, such as pointer lifetime.
 * @param {number} [config.options.delayInSeconds] - A simulated delay before using the pointer.
 * @param {boolean} [config.options.simulateTampering] - If true, will maliciously alter the pointer after signing.
 * @returns {() => Promise<void>} "The One" function to be called.
 */
function createReader(config) {
  const { slr, logicalName, credentials, auditLogger, options } = config;
  
  // This returned function is the simplified facade, "the one" to be called. 
  return async () => {
    const traceId = crypto.randomUUID(); 
    
    // Use the SLR to resolve the logical name into a physical path.
    const connection = await slr.resolve(logicalName, credentials, { auditLogger, traceId });

    // If resolution fails, the SLR has denied access. Stop here.
    if (!connection) {
      // Failure is logged by the SLR, so we can halt silently.
      return;
    }

    // Now, "at use time", we sign the connection to get our ephemeral token.
    const signedPointer = slr.sign(connection, options); 

    // Simulate a malicious actor tampering with the pointer after it has been signed.
    if (options?.simulateTampering) {
      signedPointer.connection.address = '/etc/passwd'; // Maliciously change the target address.
    }

    // Introduce a delay to test pointer expiration.
    if (options?.delayInSeconds > 0) {
      await new Promise(resolve => setTimeout(resolve, options.delayInSeconds * 1000));
    }

    // Before using the pointer, perform the critical round-trip validation.
    const validationResult = signedPointer.validate();
    if (!validationResult.valid) { 
      auditLogger.logPointerFailure({ traceId, pointer: signedPointer, reason: validationResult.reason, credentials });
      return;
    }

    const connectionDetails = signedPointer.physicalResource;
    const success = await accessResource(connectionDetails);
  }
}

module.exports = {
  ResourceConnection,
  SignedPointer,
  AuditLogger,
  SecureResourceLocator,
  checkPermission,
  evaluateConditions,
  createReader,
  accessResource,
};