const { ResourceConnection, SignedPointer } = require('./myapp.js'); // Corrected import path
const { WeatherResolvedQube, StrategicPlanQube, FeedbackLoggerQube, StockDataQube } = require('./qube_implementations');

// ===================================================================================
// 1. Qube Implementations
// ===================================================================================

// ===================================================================================
// 2. Qube Factory
// ===================================================================================

/**
 * The QubeFactory is responsible for creating the correct Qube instance based on z-address.
 * This decouples the resolver from the concrete Qube implementations.
 */
class QubeFactory {
    constructor() {
        this._constructors = new Map();
    }

    /**
     * Registers a Qube constructor for a specific z-address.
     * @param {number} z_address The z-address to register.
     * @param {class} QubeConstructor The constructor for the Qube.
     */
    register(z_address, QubeConstructor) {
        this._constructors.set(z_address, QubeConstructor);
    }

    /**
     * Creates an instance of a Qube.
     * @param {number} z_address The z-address of the Qube to create.
     * @param {SignedPointer} signedPointer The ephemeral capability token.
     * @param {any} dependencies Dependencies needed by the Qube constructor (e.g., apiKey).
     * @param {number[]} neighbors An array of z-addresses representing neighboring capabilities.
     * @returns {object|null} An instance of the ResolvedQube, or null if not found.
     */
    create(z_address, signedPointer, dependencies, neighbors) {
        const QubeConstructor = this._constructors.get(z_address);
        return QubeConstructor ? new QubeConstructor(z_address, signedPointer, dependencies, neighbors) : null;
    }
}

// ===================================================================================
// 3. Core Paradigm Logic
// ===================================================================================

/**
 * Calculates the cosine similarity between two vectors, representing the angle between them.
 * A value of 1 means the vectors are identical (angle = 0).
 * A value of 0 means they are orthogonal (angle = 90 degrees).
 * @param {number[]} vecA The first vector.
 * @param {number[]} vecB The second vector.
 * @returns {number} The cosine similarity.
 */
function calculateCosineSimilarity(vecA, vecB) {
    if (vecA.length !== vecB.length) return 0;

    let dotProduct = 0;
    let magA = 0;
    let magB = 0;

    for (let i = 0; i < vecA.length; i++) {
        dotProduct += vecA[i] * vecB[i];
        magA += vecA[i] * vecA[i];
        magB += vecB[i] * vecB[i];
    }

    magA = Math.sqrt(magA);
    magB = Math.sqrt(magB);

    if (magA === 0 || magB === 0) return 0;

    return dotProduct / (magA * magB);
}

/**
 * The geometric evaluation engine. It determines if a user's context vector
 * is close enough to a resource's target vector.
 * @param {object} requirement The resource's requirement, containing the target position.
 * @param {object} context The user's context, containing their attributes.
 * @returns {{met: boolean, reason: string|null}}
 */
function evaluateGeometricPermission(requirement, context, vectorMaps) {
    const targetVector = requirement.position;
    const threshold = requirement.threshold;
    const dimensions = requirement.dimensions;

    if (!targetVector || threshold === undefined || !dimensions) {
        return { met: false, reason: 'Resource is not defined correctly within the geometric lattice (missing position, threshold, or dimensions).' };
    }

    // Dynamically construct the user's context vector based on the defined dimensions.
    const userVector = [];
    for (const dim of dimensions) {
        const userValue = context.userAttributes[dim.name];
        let vectorValue = 0;

        if (dim.type === 'numeric') {
            vectorValue = userValue || 0;
        } else if (dim.type === 'map' && vectorMaps[dim.map]) {
            vectorValue = vectorMaps[dim.map][userValue] || 0;
        }
        userVector.push(vectorValue);
    }

    if (userVector.length !== targetVector.length) {
        return { met: false, reason: `Vector dimension mismatch. Expected ${targetVector.length}, got ${userVector.length}.` };
    }

    const similarity = calculateCosineSimilarity(targetVector, userVector);

    if (similarity >= threshold) {
        return { met: true, reason: `Similarity ${similarity.toFixed(3)} meets threshold ${threshold}` };
    } else {
        return { met: false, reason: `Similarity ${similarity.toFixed(3)} is below threshold ${threshold}` };
    }
}

// Initialize and configure the factory. In a larger application, this would be
// part of the bootstrap process, dynamically registering all available Qubes.
const qubeFactory = new QubeFactory();
// Register the WeatherResolvedQube for z-address 501
qubeFactory.register(501, WeatherResolvedQube);
qubeFactory.register(702, StrategicPlanQube);
qubeFactory.register(801, FeedbackLoggerQube);
qubeFactory.register(301, StockDataQube);


async function resolveCapability(z_address, securityContext, apiKey, persistentLog, vectorMaps) {
    const resourceDefinition = persistentLog[z_address];
    if (!resourceDefinition) {
        return { success: false, error: { message: `z-address ${z_address} not found.` } };
    }

    // --- Context Building (The 'y' in z=xy) ---
    // Build a rich context for the permission evaluation.
    // In a real system, these attributes would be loaded from a user directory.
    const context = {
        user: { id: securityContext?.id || 'unknown' },
        userAttributes: securityContext?.attributes || {}
    };

    // --- Security Handshake (The 'f' in z=xy) ---
    // The evaluation is now a geometric comparison of vectors.
    const permissionResult = evaluateGeometricPermission(resourceDefinition.requiredPermission, context, vectorMaps);

    if (!permissionResult.met) {
        // Provide a detailed reason for failure.
        return { success: false, error: { message: 'Permission denied.', details: permissionResult.reason } };
    }

    // Create a ResourceConnection using details from the persistent log
    const connection = new ResourceConnection({
        protocol: resourceDefinition.connectionDetails.protocol,
        address: resourceDefinition.connectionDetails.address,
        // In a real system, encryptedCredentials would be retrieved securely here
        encryptedCredentials: null 
    });

    // Create a SignedPointer from the ResourceConnection
    const signedPointer = new SignedPointer(connection, 60); // Lifetime of 60 seconds

    // Use the factory to create the correct Qube instance
    // Pass the z_address and neighbors from the resource definition to the factory
    const qube = qubeFactory.create(z_address, signedPointer, apiKey, resourceDefinition.neighbors || []);

    // If the factory couldn't create a Qube (e.g., z-address not registered)
    if (!qube) {
        return { success: false, error: { message: `No Qube implementation for z-address ${z_address}.` } };
    }
    return { success: true, qube: qube };
}

module.exports = { resolveCapability, evaluateGeometricPermission }; // evaluateConditions is no longer used here