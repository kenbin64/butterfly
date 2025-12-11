# Tutorial: Building a To-Do List App with the Butterfly Paradigm

This tutorial demonstrates how to build a simple, multi-user To-Do List application using the Butterfly Paradigm's direct-addressing model. We will focus on how the application interacts with the paradigm's API, not the UI implementation.

## 1. The Goal

Our application will have two primary functions:
1.  `getTasks(userId)`: Fetch all tasks for a specific user.
2.  `addTask(userId, taskText)`: Add a new task for a specific user.

Crucially, the application code will be completely decoupled from the database. It will not know where the data is stored, what the database schema is, or how to connect to it. It will only know the `z`-addresses for the capabilities it needs.

---

## 2. Step 1: Defining the Resource Map (The Persistent Log)

As data administrators, the first step is to define the resource templates in our secure, persistent log (the "Connection Table"). These definitions are the metadata that will be loaded into an active Qube upon a successful request.

For our To-Do app, we need two resource definitions, each with a unique, known `z`-address.

**Resource at `z-address: 201`**
*   **Description:** The capability to read a user's list of tasks.
*   **Connection Details:** `{ protocol: 'sql', address: 'todo_database.db' }`
*   **Required Permission:** `{ action: 'read', resourceType: 'task-list', condition: 'isOwner' }`

**Resource at `z-address: 202`**
*   **Description:** The capability to write a new task for a user.
*   **Connection Details:** `{ protocol: 'sql', address: 'todo_database.db' }`
*   **Required Permission:** `{ action: 'write', resourceType: 'task', condition: 'isOwner' }`

These definitions are registered once when the system is set up. The application developer is simply told, "To read tasks, use `z=201`. To write tasks, use `z=202`."

---

## 3. Step 2: Building the Application (The Qube Consumer)

Now, we write the application code. The application has an instance of a `QubeResolver` provided to it during its startup.

```javascript
// --- ToDoApp.js ---

// Assume 'qubeResolver' is initialized and available.

/**
 * Fetches all tasks for a given user.
 * @param {string} userId - The ID of the user whose tasks are being requested.
 */
async function getTasks(userId) {
  // 1. Define the coordinate: the z-address and the security context.
  const z_address = 201; // The known address for reading task lists.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'read', resourceType: 'task-list', condition: 'isOwner' }]
  };

  // 2. Resolve the coordinate to get an active Qube.
  // The resolver will fetch the definition at z=201 and check if the user
  // (whose ID is in the context) is the owner.
  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to read tasks.`);
    return null;
  }

  // 3. Invoke the 'read' capability of the Qube.
  // The Qube itself knows how to construct and execute the correct SQL query.
  // The application code is completely ignorant of SQL.
  console.log(`User ${userId} authorized. Reading tasks...`);
  const tasksDataQube = await resolvedQube.read({ ownerId: userId });

  // 4. Interact with the returned DataQube.
  // The application receives a secure container of pointers, not raw data.
  return tasksDataQube;
}

/**
 * Adds a new task for a given user.
 * @param {string} userId - The ID of the user adding the task.
 * @param {string} taskText - The content of the new task.
 */
async function addTask(userId, taskText) {
  // 1. Define the coordinate.
  const z_address = 202; // The known address for writing a task.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'write', resourceType: 'task', condition: 'isOwner' }]
  };

  // 2. Resolve the coordinate.
  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to add a task.`);
    return false;
  }

  // 3. Invoke the 'write' capability of the Qube.
  // The Qube handles the database INSERT statement.
  console.log(`User ${userId} authorized. Writing new task...`);
  const success = await resolvedQube.write({ ownerId: userId, text: taskText });

  return success;
}
```

---

## 4. Analysis: The Power of the Paradigm

This implementation demonstrates the core philosophy of No-Iteration Programming:

*   **Zero Iteration:** The application code performs no searching. It directly addresses the capability it needs (`z=201` or `z=202`). The system's response is immediate and direct.

*   **Total Decoupling:** The `ToDoApp.js` file contains no SQL, no database connection strings, and no file paths. It could be interacting with a local SQLite database, a remote PostgreSQL cluster, or a serverless function—the application code would be **identical** in all cases.

*   **Inherent Security:** Security is not a separate step; it is part of the address itself. The `resolve` call is the single point of authorization. The application cannot bypass it. The methods (`.read()`, `.write()`) only exist on the `ResolvedQube` if the user was granted those specific privileges for that specific request.

*   **Simplicity:** The application developer's job is dramatically simplified. They no longer need to be an expert in database drivers or security protocols. They only need to know the `z`-addresses for the actions they are allowed to perform and how to build the security context for their user.

This tutorial shows that by adopting the Butterfly Paradigm, we can build applications that are simpler, more secure, and infinitely more flexible than those built with traditional, tightly-coupled architectures.