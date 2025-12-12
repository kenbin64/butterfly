# Tutorial: Dynamic Discovery with the QubeIndex

This tutorial introduces a new, crucial component of the Butterfly Paradigm: the **`QubeIndex`**. While using a known `z-address` is ideal for direct, high-speed access to a capability, applications often need to *discover* capabilities at runtime. The `QubeIndex` serves as this discovery mechanism.

## 1. The Problem: Static vs. Dynamic Applications

The To-Do app tutorials demonstrate using hardcoded `z-addresses` (`201`, `202`, etc.) to perform specific actions. This is perfect for a "Get Tasks" button, where the function is known at design time.

But what if you are building a general-purpose admin dashboard, a command-line tool, or a user interface where the user can search for available actions? In these cases, the application doesn't know what capabilities exist beforehand. It needs a way to ask the system, "What can you do?"

## 2. The Solution: The `QubeIndex`

The `QubeIndex` is a searchable "card catalog" for capabilities. Instead of just mapping a `z-address` to a resource, it stores rich metadata—like descriptions and keywords—that describe what each capability does.

An application can query this index with a search term (e.g., "weather" or "task") and receive a list of matching capabilities and their corresponding `z-addresses`.

---

## 3. Step 1: Defining the Index

The `QubeIndex` is populated by administrators with metadata about the available `z-addresses`. This index would be a secure, queryable resource, just like the `persistentLog` for the `QubeResolver`.

Here is an example of the data that would populate the index:

```javascript
const qubeIndexData = [
  {
    z_address: 201,
    name: "Get All Tasks",
    description: "Fetches a complete list of to-do tasks for a user.",
    keywords: ['todo', 'task', 'get', 'read', 'list', 'all']
  },
  {
    z_address: 204,
    name: "Search Tasks",
    description: "Searches for tasks containing a specific keyword.",
    keywords: ['todo', 'task', 'find', 'search', 'query', 'filter']
  },
  {
    z_address: 501,
    name: "Get Weather Forecast",
    description: "Fetches the 5-day weather forecast for a given city.",
    keywords: ['weather', 'forecast', 'climate', 'temperature', 'api']
  }
];
```

---

## 4. Step 2: Implementing and Using the `QubeIndex`

An application would use a `QubeIndex` client to search for capabilities. The client would have a simple `find()` method.

Here is a complete example showing how an application can dynamically discover and then use the weather forecast capability.

```javascript
// --- QubeIndex Implementation ---
class QubeIndex {
  constructor(indexData) {
    this.index = indexData;
  }

  find(searchTerm) {
    const lowerCaseTerm = searchTerm.toLowerCase();
    return this.index.filter(entry =>
      entry.keywords.some(kw => kw.toLowerCase().includes(lowerCaseTerm)) ||
      entry.description.toLowerCase().includes(lowerCaseTerm) ||
      entry.name.toLowerCase().includes(lowerCaseTerm)
    );
  }
}

// --- Application Logic ---
async function dynamicallyFindAndUseWeather(location) {
  // 1. The application queries the index to discover a capability.
  const qubeIndex = new QubeIndex(qubeIndexData);
  const searchResults = qubeIndex.find("forecast");

  if (searchResults.length === 0) {
    console.error("Discovery failed: No capability found for 'forecast'.");
    return;
  }

  // 2. The application selects the desired capability and gets its z-address.
  const weatherCapability = searchResults;
  const z_address = weatherCapability.z_address; // Dynamically discovered: 501
  console.log(`Discovered capability "${weatherCapability.name}" at z-address ${z_address}.`);

  // 3. The application uses the discovered z-address with the QubeResolver as usual.
  const securityContext = { id: 'dynamic-app-01', permissions: [{ action: 'read', resourceType: 'weather-api' }] };
  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) { /* ... handle authorization failure ... */ return; }

  // 4. Invoke the resolved capability.
  const result = await resolvedQube.read({ location: location });
  console.log(result);
}
```

## 5. Analysis: The Power of Discovery

The `QubeIndex` provides several powerful advantages:

*   **Ultimate Decoupling**: The application is no longer coupled to anything, not even a `z-address`. It only needs to know a conceptual search term for the business capability it wants to perform.
*   **Dynamic UIs**: This pattern is the foundation for building powerful, dynamic user interfaces. An application can present a search bar, allowing users to find and execute tools without the UI needing to be pre-programmed for every possible action.
*   **Extensibility**: Administrators can add new capabilities (e.g., a stock ticker with `z=301`) to the system, and as long as it's registered in the `QubeIndex` with relevant keywords, existing dynamic applications can immediately discover and use it without any code changes.

By combining the direct access of the `QubeResolver` with the dynamic discovery of the `QubeIndex`, the Butterfly Paradigm provides a complete, secure, and flexible architecture for any distributed system.