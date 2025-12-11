const fs = require('fs');
const yaml = require('js-yaml');
const crypto = require('crypto');
const fetch = require('node-fetch');
const core = require('../../core/library.js');
const PostgresStorageAdapter = require('../../core/postgres_storage_adapter.js');

/**
 * This is the main application logic for the Stock Tracker.
 * It demonstrates how a Butterfly Compliant app is built.
 */
async function main() {
  // --- 1. Secure Bootstrap ---
  // The application bootstraps itself using the core paradigm's principles.
  const configPath = process.env.APP_CONFIG_PATH;
  const publicKeyPath = process.env.APP_PUBLIC_KEY_PATH;
  if (!configPath || !publicKeyPath) {
    console.error('FATAL: APP_CONFIG_PATH and APP_PUBLIC_KEY_PATH environment variables must be set.');
    process.exit(1);
  }

  let config;
  try {
    const configContent = fs.readFileSync(configPath, 'utf8');
    const signature = fs.readFileSync(configPath + '.sig');
    const publicKey = fs.readFileSync(publicKeyPath, 'utf8');
    if (!crypto.verify(null, Buffer.from(configContent), publicKey, signature)) {
      throw new Error('Configuration file signature is invalid!');
    }
    config = yaml.load(configContent);
  } catch (err) {
    console.error(`[FATAL] Could not load or verify configuration: ${err.message}`);
    process.exit(1);
  }

  // --- 2. Initialize Core Services ---
  // The application instantiates the necessary components from the core library.
  let storageAdapter;
  if (config.storage.type === 'sqlite') {
    storageAdapter = new core.SecureResourceLocator.SqliteStorageAdapter(config.storage.sqlite);
  } else if (config.storage.type === 'postgres') {
    storageAdapter = new PostgresStorageAdapter(config.storage.postgres);
  } else {
    throw new Error(`Unsupported storage type: ${config.storage.type}`);
  }

  try {
    await storageAdapter.init();
    const qubeResolver = new core.SecureResourceLocator(storageAdapter);

    // --- 3. Application Logic ---
    const ticker = process.argv[2];
    if (!ticker) {
      console.error('Usage: node apps/stock_tracker/tracker.js <TICKER>');
      return;
    }

    // The developer knows the z-address for the stock data API capability.
    const z_address = 301; // Let's assume 301 is for the Alpha Vantage API.
    const securityContext = {
      id: 'stock-tracker-app-001',
      permissions: [{ action: 'read', resourceType: 'financial-api' }]
    };

    console.log(`Requesting capability to access stock data for ticker: ${ticker}...`);
    const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

    if (!resolvedQube) {
      console.error('Access Denied: This application is not authorized to use the financial API.');
      return;
    }

    console.log('Authorization successful. Fetching data...');
    // The Qube's .read() method is invoked. It knows how to use its internal,
    // decrypted metadata (like an API key) to make the request.
    const response = await resolvedQube.read({ ticker: ticker });

    if (response && response['Monthly Time Series']) {
      const timeSeries = response['Monthly Time Series'];
      const dates = Object.keys(timeSeries).slice(0, 12); // Last 12 months
      const latestClose = parseFloat(timeSeries[dates[0]]['4. close']);
      const yearAgoClose = parseFloat(timeSeries[dates[11]]['4. close']);
      const annualGrowth = ((latestClose - yearAgoClose) / yearAgoClose) * 100;

      console.log(`\n--- Stock Report for ${response['Meta Data']['2. Symbol']} ---`);
      console.log(`Latest Month Close: $${latestClose.toFixed(2)}`);
      console.log(`One Year Ago Close: $${yearAgoClose.toFixed(2)}`);
      console.log(`Annual Growth: ${annualGrowth.toFixed(2)}%`);
    } else {
      console.error('Could not retrieve or parse stock data. The API may have rate limited the request.');
    }

  } finally {
    if (storageAdapter) {
      await storageAdapter.close();
    }
  }
}

main();