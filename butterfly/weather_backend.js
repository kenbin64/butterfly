/**
 * weather_backend.js
 *
 * This file is the main entry point for the backend server. It follows best
 * practices by delegating all logic to dedicated modules for configuration,
 * routing, and application services. Its sole responsibility is to
 * bootstrap the application and start the Express server.
 *
 * To run this server:
 * 1. Install dependencies: `npm install express node-fetch js-yaml`
 * 2. Ensure `weather_config.yml` and its signature exist.
 * 3. Set environment variables: `APP_CONFIG_PATH` should now point to `secrets.yml`.
 * 4. Run the server: `node weather_backend.js`
 */

const express = require('express');
const { loadSecureConfig } = require('./secure_config_loader');
const yaml = require('js-yaml');
const fs = require('fs');
const { createStandardRoutes } = require('./weather_routes_standard');
const { createButterflyRoutes } = require('./weather_routes_butterfly');

function main() {
    try {
        // --- 1. Secure Bootstrap ---
        // Load and verify configuration from a secure, external module.
        console.log('Bootstrapping server: Loading and verifying configuration...');
        const config = loadSecureConfig();
        const apiKeys = {
            weather: config.weather_api.key,
            stock: config.stock_api.key
        };
        const port = config.server?.port || 3000;

        // Load the non-secret z-address registry.
        console.log('Loading z-address registry...');
        const registryContent = fs.readFileSync('./z_address_registry.yml', 'utf8');
        const zAddressRegistry = {
            current: yaml.load(registryContent) // Wrap in a container object for hot-swapping
        };

        // Load the vector maps configuration.
        console.log('Loading vector maps...');
        const vectorMapsContent = fs.readFileSync('./vector_maps.yml', 'utf8');
        const vectorMaps = yaml.load(vectorMapsContent);

        // --- 2. Initialize Express App ---
        const app = express();
        app.use(express.json());
        app.use(express.static(__dirname)); // Serve static files (HTML, CSS) from the current directory.

        // --- 3. Configure Modular Routing ---
        // Create and apply the routers, injecting all dependencies.
        const standardRouter = createStandardRoutes(apiKeys.weather);
        const butterflyRouter = createButterflyRoutes(apiKeys, zAddressRegistry, vectorMaps);
        app.use('/api/standard', standardRouter);
        app.use('/api/butterfly', butterflyRouter);

        // --- 4. Start Server ---
        app.listen(port, () => {
            console.log(`\nBackend server running successfully on http://localhost:${port}`);
            console.log('Endpoints are available:');
            console.log(`  - Standard: GET http://localhost:${port}/api/standard/weather?location=<city>`);
            console.log(`  - Butterfly: POST http://localhost:${port}/api/butterfly/resolve`);
        });

    } catch (error) {
        // If the secure bootstrap fails, log the fatal error and exit.
        console.error(error.message);
        process.exit(1);
    }
}

main();