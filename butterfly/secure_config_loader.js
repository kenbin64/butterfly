/**
 * secure_config_loader.js
 *
 * This module provides a function to securely load and verify a signed YAML
 * configuration file. It is a critical component of the secure bootstrap process.
 */

const fs = require('fs');
const yaml = require('js-yaml');
const crypto = require('crypto');

function loadSecureConfig() {
    try {
        const configPath = process.env.APP_CONFIG_PATH;
        const publicKeyPath = process.env.APP_PUBLIC_KEY_PATH;

        if (!configPath || !publicKeyPath) {
            throw new Error('APP_CONFIG_PATH and APP_PUBLIC_KEY_PATH environment variables must be set.');
        }

        const configContent = fs.readFileSync(configPath, 'utf8');
        const signature = fs.readFileSync(configPath + '.sig');
        const publicKey = fs.readFileSync(publicKeyPath, 'utf8');

        if (!crypto.verify(null, Buffer.from(configContent), publicKey, signature)) {
            throw new Error('Configuration file signature is invalid! The file may have been tampered with.');
        }

        return yaml.load(configContent);
    } catch (err) {
        // We wrap the original error to provide more context for easier debugging.
        throw new Error(`[FATAL] Could not load or verify configuration: ${err.message}`);
    }
}

module.exports = { loadSecureConfig };