/**
 * capability_os_simulation.js
 *
 * This script simulates a "Butterfly OS" kernel that uses capability-based security
 * instead of traditional access control lists. It demonstrates how the geometric
 * permission model can be applied to core operating system tasks like opening files.
 *
 * To run: `node capability_os_simulation.js`
 */

// --- 1. The File System Registry (The OS's knowledge of files) ---
const fileRegistry = {
    'doc-101': { owner: 'user-alice', type: 'text/plain', sensitivity: 2 },
    'img-202': { owner: 'user-alice', type: 'image/jpeg', sensitivity: 1 },
    'financial-report.xlsx': { owner: 'user-bob', type: 'spreadsheet', sensitivity: 5 }
};

// --- 2. The Geometric Permission Engine (The OS Kernel's Brain) ---
const VECTOR_MAPS = {
    fileType: { 'text/plain': 1, 'image/jpeg': 2, 'spreadsheet': 3 },
    action: { read: 1, write: 2 }
};

function calculateCosineSimilarity(vecA, vecB) {
    let dotProduct = 0, magA = 0, magB = 0;
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

// --- 3. The Capability Handle (The Resolved Qube) ---
/**
 * An ephemeral, secure handle to a file. It only contains the methods
 * for which it was authorized.
 */
class FileHandle {
    constructor(fileId, grantedAction) {
        this._fileId = fileId;
        this._grantedAction = grantedAction;

        if (grantedAction === 'read') {
            this.read = () => `(Simulation) Reading content of ${this._fileId}...`;
        }
        if (grantedAction === 'write') {
            this.write = (content) => `(Simulation) Writing "${content}" to ${this._fileId}...`;
        }

        // Add a proxy to intercept calls to non-existent methods.
        return new Proxy(this, {
            get(target, prop) {
                // If the property exists on the original object, return it.
                if (prop in target) return target[prop];

                // If the async runtime is checking for a '.then' property,
                // explicitly state that it doesn't exist. This prevents the error.
                if (prop === 'then') return undefined;

                throw new Error(`Capability Not Granted: The action '${prop}' was not authorized for this handle.`);
            }
        }
    }
}

// --- 4. The OS Kernel (The Qube Resolver) ---
class OSKernel {
    /**
     * The core function of the OS. It resolves a user's request to perform an
     * action on a file with a specific application.
     */
    requestCapability(userContext, request) {
        console.log(`\n[KERNEL] User '${userContext.id}' requests to '${request.action}' file '${request.fileId}' with app '${request.app.name}'.`);

        const file = fileRegistry[request.fileId];
        if (!file) {
            return { success: false, reason: `File '${request.fileId}' not found.` };
        }

        // --- Geometric Handshake ---
        // The OS defines the "ideal" context for this action as a vector.
        // Dimensions: [File Sensitivity, File Type, Action Type]
        const targetVector = [
            file.sensitivity,
            VECTOR_MAPS.fileType[file.type] || 0,
            VECTOR_MAPS.action[request.action] || 0
        ];

        // The OS constructs the user's context vector.
        const userVector = [
            userContext.clearance,
            VECTOR_MAPS.fileType[request.app.compatibleFileType] || 0,
            VECTOR_MAPS.action[request.action] || 0
        ];

        const similarity = calculateCosineSimilarity(targetVector, userVector);
        const threshold = 0.99; // Requires a very close match.

        console.log(`[KERNEL] Target Vector: [${targetVector}] (Sensitivity, FileType, Action)`);
        console.log(`[KERNEL] User/App Vector: [${userVector}]`);
        console.log(`[KERNEL] Cosine Similarity: ${similarity.toFixed(4)}`);

        if (similarity < threshold) {
            return { success: false, reason: `Contextual mismatch. Similarity ${similarity.toFixed(4)} is below threshold ${threshold}.` };
        }

        console.log('[KERNEL] Access GRANTED. Creating secure file handle...');
        // If access is granted, create the ephemeral capability token (the Qube).
        const handle = new FileHandle(request.fileId, request.action);
        return { success: true, handle: handle };
    }
}

// --- 5. The Applications ---
class Application {
    constructor(name, compatibleFileType) {
        this.name = name;
        this.compatibleFileType = compatibleFileType;
    }

    // Applications start with no power. They must be given a handle to do anything.
    openFile(handle) {
        if (handle && typeof handle.read === 'function') {
            console.log(`[${this.name}] Successfully opened file. ${handle.read()}`);
        } else {
            // This branch is now less likely to be hit due to the proxy, but remains for robustness.
            console.error(`[${this.name}] ERROR: A valid file handle with 'read' capability was not provided.`);
        }
    }
}

// --- 6. Main Simulation Logic ---
function main() {
    const kernel = new OSKernel();
    const textEditor = new Application('TextEditor', 'text/plain');
    const imageViewer = new Application('ImageViewer', 'image/jpeg');

    // Define our user for this session.
    const userAlice = { id: 'user-alice', clearance: 3 };

    // --- SCENARIO 1: Success ---
    // Alice tries to open her text document with the correct application.
    let request = {
        app: textEditor,
        fileId: 'doc-101',
        action: 'read'
    };
    let result = kernel.requestCapability(userAlice, request);
    if (result.success) {
        textEditor.openFile(result.handle);
    } else {
        console.error(`[OS] Access Denied: ${result.reason}`);
    }

    // --- SCENARIO 2: Failure (Application Mismatch) ---
    // Alice tries to open her image file with the TextEditor.
    // The vectors for file type will not align, causing the similarity score to drop.
    request = {
        app: textEditor,
        fileId: 'img-202',
        action: 'read'
    };
    result = kernel.requestCapability(userAlice, request);
    if (result.success) {
        textEditor.openFile(result.handle);
    } else {
        console.error(`[OS] Access Denied: ${result.reason}`);
    }

    // --- SCENARIO 3: Failure (Security Clearance Mismatch) ---
    // Alice (clearance 3) tries to open a high-sensitivity (5) financial report.
    // The vectors for sensitivity will not align.
    request = {
        app: textEditor,
        fileId: 'financial-report.xlsx',
        action: 'read'
    };
    result = kernel.requestCapability(userAlice, request);
    if (result.success) {
        textEditor.openFile(result.handle);
    } else {
        console.error(`[OS] Access Denied: ${result.reason}`);
    }
}

main();