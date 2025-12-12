/**
 * Weather_API_Test.js
 *
 * This file demonstrates using the Butterfly Paradigm to connect to a real public-facing
 * web API. It uses a secure, signed configuration file to load credentials, proving
 * the end-to-end security of the architecture.
 *
 * To run this test:
 * 1. Install dependencies: `npm install node-fetch js-yaml`
 * 2. Create a keypair and sign the `weather_config.yml` file.
 * 3. Set environment variables:
 *    export APP_CONFIG_PATH=c:/Projects/repo/condiut/butterfly/butterfly/weather_config.yml
 *    export APP_PUBLIC_KEY_PATH=c:/Projects/repo/condiut/butterfly/butterfly/public_key.pem
 * 4. Run the file: `node c:/Projects/repo/condiut/butterfly/butterfly/Weather_API_Test.js`
 */

const fetch = require('node-fetch');
const fs = require('fs');
const yaml = require('js-yaml');
const crypto = require('crypto');

// --- 1. Define the New Capability (The "z-address") ---
// We define a new capability for fetching weather data.
const persistentLog = {
  501: {
    description: "The capability to fetch historical weather data from the Visual Crossing API.",
    connectionDetails: {
      protocol: 'https',
      address: 'weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/'
      // In a real system, the API key would be an encrypted credential here.
    },
    requiredPermission: { action: 'read', resourceType: 'weather-api' }
  }
};

// --- 2. Implement the Capability-Specific Qube ---
// This is the core of the integration. This ResolvedQube knows how to talk to the weather API.
class WeatherResolvedQube {
  constructor(resourceDefinition, grantedAction, apiKey) {
    this._connectionDetails = resourceDefinition.connectionDetails;
    this._grantedAction = grantedAction;
    this._apiKey = apiKey; // The Qube securely holds the credential.

    // Dynamically attach the 'read' method because that's what was granted.
    if (this._grantedAction === 'read') {
      this.read = this._read.bind(this);
    }
  }

  /**
   * Executes a read operation against the live weather API.
   * @param {object} query - e.g., { location: 'London,UK', date: '2023-01-01' }
   * @returns {Promise<{success: boolean, data?: object, error?: object}>} A structured result object.
   */
  async _read(query) {
    const { location, date } = query;
    console.log(`[QUBE] Invoking 'read' capability for weather in ${location} on ${date}.`);

    // The Qube is responsible for constructing the correct URL and adding credentials.
    // The application layer knows nothing about this logic.
    const fullUrl = `https://${this._connectionDetails.address}${location}/${date}?unitGroup=metric&key=${this._apiKey}&contentType=json`;

    console.log(`[QUBE] Making live API call to: ${fullUrl.replace(this._apiKey, 'REDACTED')}`);

    try {
      const response = await fetch(fullUrl);
      if (!response.ok) {
        // If the API returns a non-2xx status, capture the details in a structured error.
        const errorText = await response.text();
        console.error(`[QUBE] API request failed with status ${response.status}: ${errorText}`);
        return {
          success: false,
          error: { status: response.status, message: 'API request failed.', details: errorText }
        };
      }
      // On success, wrap the data in the standard success structure.
      const data = await response.json();
      return { success: true, data: data };
    } catch (error) {
      // Handle network errors or other exceptions during the fetch.
      console.error(`[QUBE] A network or fetch error occurred: ${error.message}`);
      return { success: false, error: { message: 'Network or client error.', details: error.message } };
    }
  }
}

// --- 3. Use the Standard QubeResolver ---
// The QubeResolver doesn't need to change. Its job is to authorize, not to implement.

function checkPermission(requirement, claims) {
  return claims.some(claim =>
    claim.action === requirement.action &&
    claim.resourceType === requirement.resourceType
  );
}

class QubeResolver {
  constructor(storage) { this._storage = storage; }

  async resolve(z_address, securityContext, apiKey) {
    const resourceDefinition = this._storage[z_address];
    if (!resourceDefinition) {
      console.error(`[RESOLVER] Error: z-address ${z_address} not found.`);
      return null;
    }

    const hasPermission = checkPermission(resourceDefinition.requiredPermission, securityContext.permissions);
    if (!hasPermission) {
      console.log(`[RESOLVER] Access Denied: User does not have the required permission.`);
      return null;
    }

    console.log(`[RESOLVER] Access Granted. Instantiating Weather Qube with 'read' capability.`);
    // For this test, we pass the API key directly to the Qube constructor.
    return new WeatherResolvedQube(resourceDefinition, 'read', apiKey);
  }
}

// --- 4. The Application/Test Logic ---
/**
 * This is our application. It only knows about z-addresses and capabilities.
 */
async function runWeatherTest() {
  // --- Secure Bootstrap ---
  // The application loads its configuration using the secure bootstrap process.
  const configPath = process.env.APP_CONFIG_PATH;
  const publicKeyPath = process.env.APP_PUBLIC_KEY_PATH;
  if (!configPath || !publicKeyPath) {
    console.error('FATAL: APP_CONFIG_PATH and APP_PUBLIC_KEY_PATH environment variables must be set.');
    return;
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
    return;
  }

  const apiKey = config.weather_api.key;

  // The application instantiates the resolver.
  const qubeResolver = new QubeResolver(persistentLog);

  // The application defines its request: a z-address and a security context.
  const z_address = 501;
  const securityContext = {
    id: 'weather-dashboard-app-001',
    permissions: [{ action: 'read', resourceType: 'weather-api' }] // This app has the required permission.
  };

  console.log('--- Running Weather API Test ---');
  console.log(`Application is requesting capability at z-address ${z_address}...`);

  // Resolve the capability. The API key is passed here for the resolver to inject.
  const resolvedQube = await qubeResolver.resolve(z_address, securityContext, apiKey);

  if (!resolvedQube) {
    console.error('TEST FAILED: Could not resolve capability.');
    return;
  }

  // Use the resolved capability. The application calls '.read()' and is completely
  // unaware that a live HTTP GET request is happening under the hood.
  const result = await resolvedQube.read({ location: 'New York, NY', date: '2024-01-10' });

  if (result.success) {
    const weatherData = result.data;
    const day = weatherData.days[0];
    console.log('\n--- TEST SUCCEEDED ---');
    console.log(`Successfully fetched weather for ${weatherData.resolvedAddress}.`);
    console.log(`Date: ${day.datetime}, Temp: ${day.temp}°C, Conditions: ${day.conditions}`);
  } else {
    // The application can now inspect the structured error from the Qube.
    console.error('\n--- TEST FAILED ---');
    console.error(`The Qube reported an error: ${result.error.message}`);
    console.error(`Details: ${result.error.details}`);
  }
}

runWeatherTest();