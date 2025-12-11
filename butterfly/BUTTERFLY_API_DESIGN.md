# The Butterfly Language: An API for a New Paradigm

## 1. Philosophy: Programming with the Butterfly Pattern

The Butterfly Language is not a new programming language. It is a universal **design pattern** and API scaffold that fundamentally alters how applications interact with data. It teaches applications and data stores a new, secure "language," eliminating the need for brittle, centralized go-betweens.

The core of this language is the **`z=xy` Qube**, a dimensional data model for locating and accessing any resource in a system.

---

## 2. The Fundamental Data Model: The `z=xy` Qube

In the Butterfly Paradigm, every data access operation is a function of resolving a location in a conceptual 3D space. This location, the **Qube (`z`)**, contains everything needed for a direct, O(1) connection to any data source—be it a database, a local file, or an address in RAM.

*   **`x` - The Logical Dimension (Width):** This represents the **Logical Name** of a resource. It is a simple, human-readable string that defines *what* is being requested.
    *   Example: `"quarterly-sales-reports"`

*   **`y` - The Contextual Dimension (Length):** This represents the full **Security Context** of the request. It defines *who* is asking, *when* they are asking, and from *where*. It includes the user's credentials, permissions, and other dynamic attributes.
    *   Example: `{ user: { id: 'analyst-007' }, permissions: [...] }`

*   **`z` - The Resolution Qube (Product):** This is the product of evaluating `x` against `y`. The **Qube (`z`)** is a secure, ephemeral data object—a **Resolved Pointer**—that contains the direct, physical path to the data. When an application holds `z`, it holds the verified *capability* to access the resource.

> The entire system is built around this principle: **Find a `z`, and you connect.**

---

## 3. The Butterfly Architectural Layers

The Butterfly Paradigm re-imagines traditional software layers (Model, Controller, Service) through its own design pattern.

### The Model Layer: The "Connection Table"

This layer represents the static "map" of all possible resources in the ecosystem. It is a collection of `x` values (Logical Names) and their corresponding physical resource templates.

*   **Analogy:** The initial state of the universe before the butterfly flaps its wings.
*   **Implementation:** A database table or a configuration service that stores mappings from logical names to connection details (protocol, address, required permissions).

### The Controller/Service Layer: The "Qube Resolver"

This is the "brain" of the paradigm—the component that calculates `z`. It takes `x` (the what) and `y` (the who/when) and uses "logic gates" to produce the Resolved Pointer (`z`).

*   **Analogy:** The complex chain of events in the atmosphere; the "truth tables" and "determination graphs" that process the initial action.
*   **Implementation:** A `QubeResolver` class that performs the security handshake, evaluates permissions using the ABAC engine (`checkPermission`), and signs the final pointer.

### The View/Application Layer: The "Qube Consumer"

This is any application that needs to access data. A Butterfly Compliant application does not contain connection logic. It only knows how to do three things:

1.  Ask a `QubeResolver` for a resource (`z`).
2.  Validate the received `z`.
3.  Use `z` to make a direct connection.

*   **Analogy:** The final, powerful outcome (the hurricane) that is experienced without needing to understand the intermediate steps.

---

## 4. The Butterfly Language API

This is the conceptual API that a developer would use to implement the paradigm.

### Core Classes

#### `class QubeResolver`
The central component that embodies the "logic gates."

```javascript
/**
 * Resolves a logical name and a security context into a secure, ephemeral pointer.
 * @param {string} logicalName - The 'x' dimension: what is being requested.
 * @param {object} securityContext - The 'y' dimension: who is requesting it.
 * @returns {Promise<ResolvedPointer | null>} The 'z' Qube, or null if access is denied.
 */
async function resolve(logicalName, securityContext);
```

#### `class ResolvedPointer`
The `z` Qube. An immutable, signed data object representing a temporary access capability.

```javascript
/**
 * Validates the pointer's cryptographic signature and expiration.
 * @returns {{valid: boolean, reason: string|null}}
 */
function validate();

/**
 * Returns the physical connection details if the pointer is valid.
 * @returns {object} E.g., { protocol: 'postgres', address: '10.0.1.55' }
 */
function getConnectionDetails();
```

#### `class DataQube` (The `z-qube` Container)
The secure, self-contained data object returned after a successful data fetch. This is the "dimensional world."

```javascript
/**
 * Retrieves a specific piece of data from within the Qube using its internal z-address.
 * This provides O(1) access to data points within the fetched dataset.
 * @param {string} internal_z_address - The internal address of the data point.
 * @returns {any | null} The requested data, or null if the address is not found.
 */
function get(internal_z_address);
```

### Core Functions

#### `function PermissionEvaluator(requirement, claims, context)`
The "truth table" engine.

```javascript
/**
 * Evaluates if a set of user claims satisfies a resource's requirement.
 * @param {object} requirement - The policy required by the resource.
 * @param {object[]} claims - The permissions held by the user.
 * @param {object} context - Dynamic attributes of the request (time, IP, etc.).
 * @returns {{met: boolean, reason: string|null}}
 */
function evaluate(requirement, claims, context);
```

---

## 5. Example Implementation Workflow

Here is how a developer would use the Butterfly Language API to fetch a user's profile.

```javascript
// 1. The application defines the 'x' and 'y' dimensions.
const logicalName = 'user-profiles/user-123'; // The 'x'
const securityContext = {
  id: 'user-123',
  permissions: [{ action: 'read', resourceType: 'profile', condition: 'isOwner' }]
}; // The 'y'

// An instance of the resolver, configured for the application.
const qubeResolver = new QubeResolver(myStorageAdapter);

async function getUserProfile() {
  // 2. The application asks the resolver to calculate 'z'.
  const z_pointer = await qubeResolver.resolve(logicalName, securityContext);

  // 3. The application validates the received pointer.
  if (!z_pointer || !z_pointer.validate().valid) {
    console.error("Access denied or pointer invalid.");
    return;
  }

  // 4. The application uses the validated pointer to make a direct connection.
  const connectionDetails = z_pointer.getConnectionDetails();

  // The 'accessResource' function knows how to use these details
  // to connect directly to the data source and returns the final DataQube.
  const userProfileQube = await accessResource(connectionDetails);

  // 5. The application interacts with the secure DataQube, not raw data.
  const userName = userProfileQube.get('user.name');
  const userEmail = userProfileQube.get('user.email');

  return { name: userName, email: userEmail };
}
```

This workflow demonstrates the entire paradigm: a simple request for `z` results in a direct, secure, and fully audited connection to the data, without the application ever needing to know the physical details itself.