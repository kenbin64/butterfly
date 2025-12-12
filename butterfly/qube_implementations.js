/**
 * qube_implementations.js
 *
 * This file contains the concrete implementations for all the different
 * types of ResolvedQubes used in the system.
 */

const fetch = require('node-fetch');

class WeatherResolvedQube {
    constructor(z_address, signedPointer, apiKey, neighbors) {
        this.z_address = z_address;
        this._signedPointer = signedPointer;
        this._apiKey = apiKey;
        this._connectionDetails = signedPointer.physicalResource;
        this.neighbors = neighbors;
    }

    async read({ location }) {
        const validationResult = this._signedPointer.validate();
        if (!validationResult.valid) {
            return { success: false, error: { message: 'Invalid or expired capability token.', details: validationResult.reason } };
        }

        const fullUrl = `https://${this._connectionDetails.address}${location}/next5days?unitGroup=metric&key=${this._apiKey}&contentType=json`;
        try {
            const response = await fetch(fullUrl);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `API responded with status ${response.status}`);
            }
            const data = await response.json();
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: { message: 'API request failed inside Qube.', details: error.message } };
        }
    }
}

class StrategicPlanQube {
    constructor(z_address, signedPointer, dependencies, neighbors) {
        this.z_address = z_address;
        this._signedPointer = signedPointer;
        this.neighbors = neighbors;
        this._connectionDetails = signedPointer.physicalResource;
    }

    async read(params) {
        const validationResult = this._signedPointer.validate();
        if (!validationResult.valid) {
            return { success: false, error: { message: 'Invalid or expired capability token.', details: validationResult.reason } };
        }
        console.log(`[QUBE] Securely accessing document at SFS path: ${this._connectionDetails.address}`);
        return {
            success: true,
            data: { message: "Access granted.", secureLink: `sfs-link-for://${this._connectionDetails.address}` }
        };
    }
}

class FeedbackLoggerQube {
    constructor(z_address, signedPointer, dependencies, neighbors) {
        this.z_address = z_address;
        this._signedPointer = signedPointer;
        this.neighbors = neighbors;
        this._connectionDetails = signedPointer.physicalResource;
    }

    async write(params) {
        const validationResult = this._signedPointer.validate();
        if (!validationResult.valid) {
            return { success: false, error: { message: 'Invalid or expired capability token.', details: validationResult.reason } };
        }
        const feedback = params.feedbackText || 'No feedback provided.';
        console.log(`[QUBE] Writing to log service '${this._connectionDetails.address}': "${feedback}"`);
        return { success: true, data: { message: "Feedback logged successfully.", loggedText: feedback } };
    }
}

class StockDataQube {
    constructor(z_address, signedPointer, apiKey, neighbors) {
        this.z_address = z_address;
        this._signedPointer = signedPointer;
        this._apiKey = apiKey;
        this.neighbors = neighbors;
        this._connectionDetails = signedPointer.physicalResource;
    }

    async read(params) {
        const validationResult = this._signedPointer.validate();
        if (!validationResult.valid) {
            return { success: false, error: { message: 'Invalid or expired capability token.', details: validationResult.reason } };
        }
        const symbol = params.symbol;
        const fullUrl = `https://${this._connectionDetails.address}?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${this._apiKey}`;
        const response = await fetch(fullUrl);
        const data = await response.json();
        return { success: true, data: data };
    }
}

module.exports = { WeatherResolvedQube, StrategicPlanQube, FeedbackLoggerQube, StockDataQube };