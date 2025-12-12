/**
 * ToDoApp_Implementation.js
 *
 * This file provides a simplified, concrete implementation of the core
 * components of the Butterfly Paradigm, tailored specifically for the
 * To-Do app tutorials (get, add, delete, and search tasks).
 */

// --- 1. Mock Persistent Log & Database ---
// In a real system, this would be a secure database or configuration service.
// It maps the known z-addresses to their resource definitions.
const persistentLog = {
  201: {
    description: "The capability to read a user's list of tasks.",
    connectionDetails: { protocol: 'sql', address: 'todo_database.db' },
    requiredPermission: {
      operator: 'AND',
      clauses: [{ action: 'read', resourceType: 'task-list' }, 'isOwner']
    }
  },
  202: {
    description: "The capability to write a new task for a user.",
    connectionDetails: { protocol: 'sql', address: 'todo_database.db' },
    requiredPermission: {
      operator: 'AND',
      clauses: [{ action: 'write', resourceType: 'task' }, 'isOwner']
    }
  },
  203: {
    description: "The capability to delete a single task, provided the user is the owner.",
    connectionDetails: { protocol: 'sql', address: 'todo_database.db' },
    requiredPermission: {
      operator: 'AND',
      clauses: [{ action: 'delete', resourceType: 'task' }, 'isOwner']
    }
  },
  204: {
    description: "The capability to search a user's tasks by keyword.",
    connectionDetails: { protocol: 'sql', address: 'todo_database.db' },
    requiredPermission: {
      operator: 'AND',
      clauses: [{ action: 'search', resourceType: 'task-list' }, 'isOwner']
    }
  }
};

// A mock database object to simulate SQL operations.
const mockDatabase = {
  // The query method is now async to better simulate real database drivers.
  query: async (sql, params) => {
    console.log(`[DATABASE] Executing SQL: "${sql}" with params:`, params || 'none');

    // Simulate a potential database error for demonstration purposes.
    if (params && params.includes('fail')) {
      throw new Error('Simulated database constraint violation.');
    }

    if (sql.includes('LIKE')) { // Search
      return [{ id: 2, text: 'Walk the dog', owner_id: params[0] }];
    }
    if (sql.startsWith('SELECT')) { // Get all
      return [{ id: 1, text: 'Buy milk', owner_id: params[0] }, { id: 2, text: 'Walk the dog', owner_id: params[0] }];
    }
    return { success: true }; // For INSERT, DELETE operations.
  }
};

// --- 2. The Permission Evaluator (The Logic Gate Engine) ---
/**
 * Evaluates a condition node against the request context. This is the logic gate.
 * @param {object|string} node - The condition node to evaluate.
 * @param {object} context - The request context.
 * @param {object[]} claims - The permissions held by the user.
 * @returns {{met: boolean, reason: string|null}}
 */
function evaluateConditions(node, context, claims) {
    if (!node) return { met: true, reason: null };

    // Base case: The node is a simple permission check (action/resourceType)
    if (node.action && node.resourceType) {
        const hasClaim = claims.some(claim => {
            const actionMatch = claim.action === '*' || claim.action === node.action;
            if (!actionMatch) return false;

            // Standard string match or wildcard
            let resourceMatch = claim.resourceType === '*' || claim.resourceType === node.resourceType;

            // Regex-based determination graph matching
            if (claim.resourceType && claim.resourceType.startsWith('regex:')) {
                try {
                    const pattern = new RegExp(claim.resourceType.substring(6));
                    resourceMatch = pattern.test(node.resourceType);
                } catch (e) {
                    console.error(`[EVALUATOR] Invalid regex in claim: ${claim.resourceType}`);
                    resourceMatch = false;
                }
            }
            return resourceMatch;
        });
        return hasClaim
            ? { met: true, reason: null }
            : { met: false, reason: `Missing required claim: {action: '${node.action}', resourceType: '${node.resourceType}'}` };
    }

    // Base case: The node is a string-based condition
    if (typeof node === 'string') {
        let conditionMet = false;
        let reason = `Condition '${node}' failed`;

        switch (node) {
            case 'isOwner':
                // The resolver checks if the user *has a claim* that includes this condition.
                conditionMet = claims.some(claim => claim.condition === 'isOwner');
                if (!conditionMet) reason = `Condition '${node}' failed: User does not have an ownership-based claim.`;
                break;
            case 'isWeekend':
                const day = context.time.day;
                conditionMet = (day === 0 || day === 6); // 0=Sun, 6=Sat
                break;
            default:
                return { met: false, reason: `Unknown condition '${node}'` };
        }
        return conditionMet ? { met: true, reason: null } : { met: false, reason: reason };
    }

    // Recursive step: The node is a logical operator
    if (node.operator === 'AND') {
        for (const clause of node.clauses) {
            const result = evaluateConditions(clause, context, claims);
            if (!result.met) return { met: false, reason: `AND clause failed: ${result.reason}` };
        }
        return { met: true, reason: null };
    }

    if (node.operator === 'OR') {
        // This part is included for completeness, though not used in the current config.
        for (const clause of node.clauses) {
            if (evaluateConditions(clause, context, claims).met) return { met: true, reason: null };
        }
        return { met: false, reason: `All OR clauses failed.` };
    }

    return { met: false, reason: `Unknown operator '${node.operator}'` };
}

// --- 3. The ResolvedQube Class (The Active Capability) ---
/**
 * The active, ephemeral capability object. Its methods are determined by the
 * permissions granted during its creation.
 */
class ResolvedQube {
  constructor(resourceDefinition, grantedAction) {
    this._connectionDetails = resourceDefinition.connectionDetails;
    this._grantedAction = grantedAction;

    // Dynamically attach methods based on the granted action.
    // This enforces the capability-based API.
    if (this._grantedAction === 'read') {
      this.read = this._read.bind(this);
    }
    if (this._grantedAction === 'write') {
      this.write = this._write.bind(this);
    }
    if (this._grantedAction === 'delete') {
      this.delete = this._delete.bind(this);
    }
    if (this._grantedAction === 'search') {
      this.search = this._search.bind(this);
    }
  }

  /**
   * Executes a read operation. This method only exists if 'read' was granted.
   * @param {object} query - e.g., { ownerId: 'user-123' }
   * @returns {Promise<{success: boolean, data?: object[], error?: object}>} A structured result object.
   */
  async _read(query) {
    console.log(`[QUBE] Invoking 'read' capability for owner: ${query.ownerId}`);
    const sql = `SELECT * FROM tasks WHERE owner_id = ?;`;
    const params = [query.ownerId];
    try {
      const data = await mockDatabase.query(sql, params);
      return { success: true, data: data };
    } catch (error) {
      console.error(`[QUBE] Error during read operation: ${error.message}`);
      return { success: false, error: { message: 'Database read failed.', details: error.message } };
    }
  }

  /**
   * Executes a write operation. This method only exists if 'write' was granted.
   * @param {object} data - e.g., { ownerId: 'user-123', text: 'New Task' }
   * @returns {Promise<{success: boolean, error?: object}>} A structured result object.
   */
  async _write(data) {
    console.log(`[QUBE] Invoking 'write' capability for owner: ${data.ownerId}`);
    const sql = `INSERT INTO tasks (owner_id, text) VALUES (?, ?);`;
    const params = [data.ownerId, data.text];
    try {
      await mockDatabase.query(sql, params);
      return { success: true };
    } catch (error) {
      console.error(`[QUBE] Error during write operation: ${error.message}`);
      return { success: false, error: { message: 'Database write failed.', details: error.message } };
    }
  }

  /**
   * Executes a delete operation. This method only exists if 'delete' was granted.
   * @param {object} data - e.g., { ownerId: 'user-123', id: 'task-456' }
   * @returns {Promise<{success: boolean, error?: object}>} A structured result object.
   */
  async _delete(data) {
    console.log(`[QUBE] Invoking 'delete' capability for task: ${data.id}`);
    const sql = `DELETE FROM tasks WHERE id = ? AND owner_id = ?;`;
    const params = [data.id, data.ownerId];
    try {
      await mockDatabase.query(sql, params);
      return { success: true };
    } catch (error) {
      console.error(`[QUBE] Error during delete operation: ${error.message}`);
      return { success: false, error: { message: 'Database delete failed.', details: error.message } };
    }
  }

  /**
   * Executes a search operation. This method only exists if 'search' was granted.
   * @param {object} query - e.g., { ownerId: 'user-123', term: 'dog' }
   * @returns {Promise<{success: boolean, data?: object[], error?: object}>} A structured result object.
   */
  async _search(query) {
    console.log(`[QUBE] Invoking 'search' capability for owner: ${query.ownerId} with term: "${query.term}"`);
    const sql = `SELECT * FROM tasks WHERE owner_id = ? AND text LIKE ?;`;
    const params = [query.ownerId, `%${query.term}%`];
    try {
      const data = await mockDatabase.query(sql, params);
      return { success: true, data: data };
    } catch (error) {
      console.error(`[QUBE] Error during search operation: ${error.message}`);
      return { success: false, error: { message: 'Database search failed.', details: error.message } };
    }
  }
}

// --- 4. The QubeResolver Class (The Authorization Gatekeeper) ---
/**
 * The central component that resolves a request into a `ResolvedQube`.
 */
class QubeResolver {
  constructor(storage) {
    // The resolver is configured with a storage adapter to access the log.
    this._storage = storage;
  }

  /**
   * The core function of the paradigm. It authorizes a request and, if
   * successful, returns an active `ResolvedQube`.
   * @param {number} z_address - The direct address of the resource definition.
   * @param {object} securityContext - The user's identity and permissions.
   * @returns {Promise<ResolvedQube | null>}
   */
  async resolve(z_address, securityContext) {
    console.log(`[RESOLVER] Attempting to resolve z-address ${z_address} for user ${securityContext?.id || 'unknown'}`);

    // 1. Fetch the resource definition from the persistent log.
    const resourceDefinition = this._storage[z_address];
    if (!resourceDefinition) {
      console.error(`[RESOLVER] Error: z-address ${z_address} not found.`);
      return null; // Fail securely
    }

    // 2. Build context and perform the security handshake using the logic gate evaluator.
    const context = {
        user: { id: securityContext?.id || 'unknown' },
        time: { day: new Date().getUTCDay() } // Add time context for conditions
    };

    const permissionResult = evaluateConditions(
        resourceDefinition.requiredPermission,
        context,
        securityContext?.permissions || []
    );

    if (!permissionResult.met) {
      console.log(`[RESOLVER] Access Denied for user ${context.user.id}: ${permissionResult.reason}`);
      return null;
    }

    // 3. If authorized, instantiate and return the active Qube.
    // The Qube is created with the specific action that was granted.
    // Find the action from the permission clauses to pass to the constructor.
    const actionClause = resourceDefinition.requiredPermission.clauses.find(c => c.action);
    const grantedAction = actionClause?.action;
    console.log(`[RESOLVER] Access Granted. Instantiating Qube with '${grantedAction}' capability.`);
    const resolvedQube = new ResolvedQube(resourceDefinition, grantedAction);

    return resolvedQube;
  }
}

// Example usage:
// const qubeResolver = new QubeResolver(persistentLog);
// And then call `qubeResolver.resolve(...)` as shown in the tutorials.
