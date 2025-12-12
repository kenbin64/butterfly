/**
 * ToDoApp.js
 *
 * This file consolidates all the application-side logic for the To-Do app,
 * demonstrating how to interact with the Butterfly Paradigm for various
 * capabilities.
 *
 * It assumes a `qubeResolver` instance is initialized and available in the
 * scope where these functions are called.
 */

// --- Capability: Get All Tasks (z=201) ---
/**
 * Fetches all tasks for a given user.
 * @param {string} userId - The ID of the user whose tasks are being fetched.
 * @returns {Promise<object[]|null>} An array of task objects or null on failure.
 */
async function getTasks(userId) {
  const z_address = 201; // The known address for reading a task list.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'read', resourceType: 'task-list', condition: 'isOwner' }]
  };

  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to read tasks.`);
    return null;
  }

  console.log(`User ${userId} authorized. Fetching all tasks...`);
  const tasks = await resolvedQube.read({ ownerId: userId });
  return tasks;
}

// --- Capability: Add a Task (z=202) ---
/**
 * Adds a new task for a given user.
 * @param {string} userId - The ID of the user adding the task.
 * @param {string} taskText - The content of the new task.
 * @returns {Promise<boolean>} True on success, false on failure.
 */
async function addTask(userId, taskText) {
  const z_address = 202; // The known address for writing a new task.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'write', resourceType: 'task', condition: 'isOwner' }]
  };

  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to add a task.`);
    return false;
  }

  console.log(`User ${userId} authorized. Adding new task...`);
  const success = await resolvedQube.write({ ownerId: userId, text: taskText });
  return success;
}

// --- Capability: Delete a Task (z=203) ---
/**
 * Deletes a specific task for a given user.
 * @param {string} userId - The ID of the user deleting the task.
 * @param {string} taskId - The ID of the task to be deleted.
 * @returns {Promise<boolean>} True on success, false on failure.
 */
async function deleteTask(userId, taskId) {
  const z_address = 203; // The known address for deleting a task.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'delete', resourceType: 'task', condition: 'isOwner' }]
  };

  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to delete task ${taskId}.`);
    return false;
  }

  console.log(`User ${userId} authorized. Deleting task ${taskId}...`);
  const success = await resolvedQube.delete({ ownerId: userId, id: taskId });
  return success;
}

// --- Capability: Search Tasks (z=204) ---
/**
 * Searches for tasks containing a specific term for a given user.
 * @param {string} userId - The ID of the user whose tasks are being searched.
 * @param {string} searchTerm - The keyword to search for.
 * @returns {Promise<object[]|null>} An array of matching tasks or null on failure.
 */
async function searchTasks(userId, searchTerm) {
  const z_address = 204; // The known address for searching tasks.
  const securityContext = {
    id: userId,
    permissions: [{ action: 'search', resourceType: 'task-list', condition: 'isOwner' }]
  };

  const resolvedQube = await qubeResolver.resolve(z_address, securityContext);

  if (!resolvedQube) {
    console.error(`Access denied for user ${userId} to search tasks.`);
    return null;
  }

  console.log(`User ${userId} authorized. Searching for tasks with term: "${searchTerm}"...`);
  const results = await resolvedQube.search({ ownerId: userId, term: searchTerm });
  return results;
}