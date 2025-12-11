const pg = require('pg');

/**
 * A storage adapter for persisting connections and audit logs to PostgreSQL.
 * This class adheres to the storage adapter interface required by the Butterfly Paradigm.
 */
class PostgresStorageAdapter {
  constructor(config) {
    // 1. The pool is created once during construction.
    this.pool = new pg.Pool(config.connectionOptions);
    // Caching and metrics would be initialized here as well.
    this.connectionCache = new Map();
    this.cacheTTL = 5 * 60 * 1000;
    this.cacheMetrics = { hits: 0, misses: 0 };
  }

  async init() {
    await this._query(`
      CREATE TABLE IF NOT EXISTS connections (
        logical_name TEXT PRIMARY KEY,
        protocol TEXT NOT NULL,
        address TEXT NOT NULL,
        encrypted_credentials TEXT,
        required_permission TEXT NOT NULL
      )
    `);
    await this._query(`
      CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        trace_id TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        type TEXT NOT NULL,
        reason TEXT,
        user_id TEXT,
        resource TEXT
      )
    `);
  }

  // Helper to query using the connection pool.
  async _query(sql, params = []) {
    // 2. Every query borrows a connection from the pool and releases it.
    const client = await this.pool.connect();
    try {
      return await client.query(sql, params);
    } finally {
      client.release();
    }
  }

  async registerConnection({ logicalName, connectionDetails, requiredPermission }) {
    const { protocol, address, encryptedCredentials } = connectionDetails;
    const sql = `
      INSERT INTO connections (logical_name, protocol, address, encrypted_credentials, required_permission) 
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (logical_name) DO UPDATE SET
        protocol = EXCLUDED.protocol,
        address = EXCLUDED.address,
        encrypted_credentials = EXCLUDED.encrypted_credentials,
        required_permission = EXCLUDED.required_permission
    `;
    this.connectionCache.delete(logicalName);
    await this._query(sql, [logicalName, protocol, address, encryptedCredentials, requiredPermission]);
  }

  async getConnection(logicalName) {
    const cachedEntry = this.connectionCache.get(logicalName);
    if (cachedEntry && Date.now() < cachedEntry.expiresAt) {
      this.cacheMetrics.hits++;
      return cachedEntry.data;
    }

    this.cacheMetrics.misses++;
    const result = await this._query('SELECT * FROM connections WHERE logical_name = $1', [logicalName]);
    const row = result.rows[0];

    if (row) {
      this.connectionCache.set(logicalName, {
        data: row,
        expiresAt: Date.now() + this.cacheTTL,
      });
    }
    return row;
  }

  async logEvent(event) {
    const sql = `INSERT INTO audit_logs (trace_id, timestamp, type, reason, user_id, resource) VALUES ($1, $2, $3, $4, $5, $6)`;
    const resourceString = typeof event.resource === 'string' ? event.resource : JSON.stringify(event.resource);
    await this._query(sql, [event.traceId, event.timestamp, event.type, event.reason, event.userId, resourceString]);
  }

  getCacheMetrics() {
    return this.cacheMetrics;
  }

  async close() {
    // 3. The close method drains and closes all connections in the pool.
    await this.pool.end();
  }
}

module.exports = PostgresStorageAdapter;