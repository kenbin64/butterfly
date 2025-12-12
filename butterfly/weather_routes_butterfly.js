const express = require('express');
const { performance } = require('perf_hooks');
const { resolveCapability, evaluateGeometricPermission } = require('./weather_paradigm_core');
const fs = require('fs');
const yaml = require('js-yaml');

function createButterflyRoutes(apiKeys, zAddressRegistry, vectorMaps) {
    const router = express.Router();

    router.post('/resolve', async (req, res) => {
        const startTime = performance.now();
        const { z_address, securityContext, params } = req.body;

        // Determine which API key to use based on the z-address range.
        let apiKeyToUse;
        if (z_address >= 300 && z_address < 400) {
            apiKeyToUse = apiKeys.stock;
        } else if (z_address >= 500 && z_address < 600) {
            apiKeyToUse = apiKeys.weather;
        }

        // 1. Resolve the capability (Authorization)
        // Pass all dependencies to the resolver.
        const resolveResult = await resolveCapability(z_address, securityContext, apiKeyToUse, zAddressRegistry.current, vectorMaps);

        if (!resolveResult.success) {
            const endTime = performance.now();
            return res.status(403).json({
                ...resolveResult,
                backendProcessingTime: endTime - startTime
            });
        }

        // 2. Invoke the capability (Execution)
        const qube = resolveResult.qube;
        const actionToPerform = securityContext.attributes?.action || 'read';

        // --- Security Hardening ---
        // 1. Prevent prototype pollution by checking against a whitelist of allowed actions.
        const ALLOWED_ACTIONS = ['read', 'write', 'execute'];
        if (!ALLOWED_ACTIONS.includes(actionToPerform)) {
            return res.status(400).json({ success: false, error: { message: `Invalid action '${actionToPerform}'.` } });
        }
        // 2. Ensure the method actually exists on the resolved Qube instance.
        if (typeof qube[actionToPerform] !== 'function') {
            return res.status(405).json({
                success: false,
                error: { message: `Method Not Allowed: The resolved Qube does not support the '${actionToPerform}' action.` }
            });
        }

        // 3. Correctly call the dynamic method on the Qube instance.
        const executionResult = await qubeactionToPerform;

        const endTime = performance.now();
        res.json({
            ...executionResult,
            backendProcessingTime: endTime - startTime
        });
    });

    router.get('/index', (req, res) => {
        const { term } = req.query;
        if (!term) {
            return res.status(400).json({ error: 'Search term is required.' });
        }

        const registry = zAddressRegistry.current;
        const lowerCaseTerm = term.toLowerCase();
        const results = [];

        for (const z_address in registry) {
            const entry = registry[z_address];
            const ui = entry.ui;
            if (ui && (
                ui.keywords.some(kw => kw.toLowerCase().includes(lowerCaseTerm)) ||
                ui.name.toLowerCase().includes(lowerCaseTerm)
            )) {
                results.push({ z_address: parseInt(z_address), ...ui });
            }
        }
        res.json(results);
    });

    router.post('/admin/reload-registry', (req, res) => {
        const { securityContext } = req.body;

        // 1. Secure this endpoint using the same geometric model as other capabilities.
        const adminRequirement = {
            dimensions: [
                { name: 'action', type: 'map', map: 'action' },
                { name: 'clearance', type: 'numeric' }
            ],
            position: [4, 5], // A unique vector for this action: action=admin(4), clearance=5
            threshold: 1.0 // Must be an exact match.
        };
        const context = { user: { id: securityContext?.id || 'unknown' }, userAttributes: securityContext?.attributes || {} };
        const permissionResult = evaluateGeometricPermission(adminRequirement, context, vectorMaps);

        if (!permissionResult.met) {
            return res.status(403).json({ success: false, error: { message: 'Permission denied to reload registry.' } });
        }

        // 2. If authorized, perform the hot reload.
        try {
            console.log(`[ADMIN] User '${context.user.id}' triggered registry reload.`);
            const registryContent = fs.readFileSync('./z_address_registry.yml', 'utf8');
            const newRegistry = yaml.load(registryContent);

            // 3. Atomically swap the current registry with the new one.
            // Because zAddressRegistry is an object passed by reference, this update
            // will be reflected for all subsequent requests to /resolve and /index.
            zAddressRegistry.current = newRegistry;

            console.log('[ADMIN] z-address registry reloaded successfully.');
            res.json({ success: true, message: 'Z-address registry reloaded successfully.' });

        } catch (error) {
            console.error(`[ADMIN] Failed to reload z-address registry: ${error.message}`);
            res.status(500).json({ success: false, error: { message: 'Failed to read or parse the registry file.', details: error.message } });
        }
    });

    return router;
}

module.exports = { createButterflyRoutes };