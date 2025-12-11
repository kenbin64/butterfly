# Tutorial: Adding Search to the To-Do App with the QubeIndex

This tutorial builds upon the "Building a To-Do List App" tutorial. We will add a search feature that allows users to discover `z`-addresses for capabilities related to their tasks.

## 1. The Goal

We will create a new function, `discoverCapabilities(userId, searchQuery)`, that allows a user to search for actions they can perform. For example, searching for "add" should help them find the capability to add a new task.

This demonstrates the crucial two-step "Find, then Resolve" workflow that separates public discovery from secure authorization.

---

## 2. Step 1: Populating the QubeIndex (The "Card Catalog")

As data administrators, alongside defining our resource templates in the persistent log, we must also populate our `QubeIndex` (e.g., an Elasticsearch cluster) with public, searchable metadata.

The index contains no secrets, only public information that maps search terms to `z`-addresses.

**Index Document 1:**
```json
{
  "z_address": 201,
  "metadata": {
    "friendly_name": "get-user-tasks",
    "description": "Read and view your list of to-do items.",
    "tags": ["todo", "tasks", "read", "view", "list"]
  }
}
```

**Index Document 2:**
```json
{
  "z_address": 202,
  "metadata": {
    "friendly_name": "add-new-task",
    "description": "Create and add a new to-do item to your list.",
    "tags": ["todo", "tasks", "write", "add", "create"]
  }
}
```

---

## 3. Step 2: Building the Search Feature

Now, we add the discovery logic to our application. The application has instances of both a `QubeIndex` and a `QubeResolver`.

```javascript
// --- ToDoApp_Search.js ---

// Assume 'qubeIndex' and 'qubeResolver' are initialized and available.

/**
 * Discovers capabilities available to a user based on a search query.
 * @param {string} userId - The ID of the user performing the search.
 * @param {string} searchQuery - The user's search term (e.g., "add task").
 * @returns {Promise<object[]>} A list of authorized capabilities.
 */
async function discoverCapabilities(userId, searchQuery) {
  // 1. Find (Discovery): Query the public index for matching z-addresses.
  // This step is fast and does not involve any security checks.
  console.log(`Searching index for query: "${searchQuery}"...`);
  const potential_z_addresses = await qubeIndex.find(searchQuery); // e.g., returns

  if (potential_z_addresses.length === 0) {
    console.log('No capabilities found matching that query.');
    return [];
  }

  // 2. Resolve (Authorization): For each potential address, check if the user
  // is actually authorized to access it.
  console.log(`Found potential addresses: [${potential_z_addresses}]. Verifying permissions for user ${userId}...`);
  const authorizedCapabilities = [];
  const securityContext = {
    id: userId,
    // The user's full set of permissions.
    permissions: [{ action: 'write', resourceType: 'task', condition: 'isOwner' }]
  };

  for (const address of potential_z_addresses) {
    const resolvedQube = await qubeResolver.resolve(address, securityContext);

    // If resolve() returns a Qube, the user is authorized.
    if (resolvedQube) {
      console.log(`- User is authorized for z-address ${address}.`);
      authorizedCapabilities.push({
        z_address: address,
        description: `Capability to perform action related to z-address ${address}.` // In a real app, you'd fetch the description.
      });
    } else {
      console.log(`- User is NOT authorized for z-address ${address}.`);
    }
  }

  return authorizedCapabilities;
}
```

---

## 4. Analysis: Secure Discovery

This workflow perfectly demonstrates the separation of concerns that makes the paradigm so secure:

*   **Public Discovery, Private Authorization:** The search against the `QubeIndex` is a "public" operation. It reveals potential paths but grants no access. The actual access control happens in the `resolve` step, which is a secure, private operation for each user.
*   **Zero Trust Search:** The application doesn't trust the search results. It treats each `z`-address returned by the index as a candidate that *must* be verified against the user's specific security context.
*   **Dynamic UI:** This pattern allows you to build a dynamic user interface. A search bar can call `discoverCapabilities()`, and the UI can then render buttons or links only for the actions the user is *actually authorized* to perform, preventing "access denied" errors and creating a smoother user experience.