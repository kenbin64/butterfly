# Tutorial: Connecting a Single App to a Single Datastore

This guide provides a practical, step-by-step walkthrough for the most fundamental use case of the Butterfly System: securely connecting a single application to a single datastore.

**The Goal:** Our application (`my-app`) needs to read data from a local JSON file (`my_data.json`). However, the application should not know the file's physical path. Instead, it will use the Butterfly System as a secure middleware to access the data through an abstract pointer.

**Scenario:**
*   **The Application:** A simple Python script (`example_client.py`).
*   **The Datastore:** A local file named `my_data.json`.
*   **The Middleware:** The Butterfly System server (`app.py`).

---

## Prerequisites

1.  You have cloned the project and installed the dependencies from `requirements.txt`.
2.  You have run the first-time setup wizard for `app.py`.
3.  You have set your `BUTTERFLY_ENCRYPTION_KEY` and `JWT_SECRET_KEY` environment variables.
4.  The Butterfly server is running in a terminal: `python app.py`.

---

## Step 1: Create Your Datastore

In the root of the project directory, create a simple JSON file named `my_data.json`:

```json
{
  "user_id": "u-123",
  "preferences": {
    "theme": "dark",
    "notifications": true
  }
}
```
This file represents the sensitive data our application needs to access.

## Step 2: Create an Administrative Domain

Every connection and pointer must live inside a **Domain** that is owned by your application.

In a new terminal, run the following admin command. We will use `my-app` as our application's unique ID (`app_id`).

```bash
# Usage: python app.py --create-domain <your_app_id> "<Your Domain Name>"
python app.py --create-domain my-app "My App's Domain"
```

The system will output the details of your new domain. **Copy the `id` of the domain (e.g., `dom_...`)**. You will need it in the next step.

## Step 3: Create a Pointer to the Datastore

Now, we will tell the Butterfly System about our datastore by creating a pointer to it. We will do this using the `example_client.py` script.

Modify the `example_client.py` script. Change the `app_id` to `"my-app"` and replace the `example_query` with the following `create_pointer` action:

```python
# In example_client.py

# ... (rest of the script)

if __name__ == '__main__':
    # ... (key loading)

    client = ButterflyClient("http://localhost:5001", "my-app", JWT_SECRET, ENCRYPTION_KEY.encode())

    # --- Create a Pointer to our JSON file ---
    # Get the absolute path to my_data.json
    data_file_path = os.path.abspath("my_data.json")

    create_pointer_query = {
        "action": "create_pointer",
        "description": "Pointer to user preferences file",
        "data_reference": f"file://{data_file_path}",
        "tags": ["user_data", "preferences"]
    }
    result = client.invoke(create_pointer_query)

    print("\n--- Decrypted Response ---")
    print(json.dumps(result, indent=2))
```

Run the script: `python example_client.py`.

The system will create a new pointer. **Copy the `address` of the pointer (e.g., `ptr_...`)** from the output.

## Step 4: Create and Assign a Connection

Currently, the pointer exists but is inaccessible. We need to create a **Connection** (a permission gateway) and assign the pointer to it.

Modify `example_client.py` again. This time, we will perform two actions in a row. Replace the previous query with these:

```python
# In example_client.py

# ... (inside if __name__ == '__main__':)

domain_id = "dom_..." # Paste the Domain ID from Step 2
pointer_address = "ptr_..." # Paste the Pointer Address from Step 3

# 1. Create the Connection
create_connection_query = {
    "action": "create_connection",
    "domain_id": domain_id,
    "name": "User Preferences Access"
}
conn_result = client.invoke(create_connection_query)
connection_id = conn_result.get("result", {}).get("connection", {}).get("id")

if not connection_id:
    print("Failed to create connection. Aborting.")
else:
    print(f"\n[*] Connection created with ID: {connection_id}")
    # 2. Assign the Pointer to the Connection
    assign_pointer_query = {
        "action": "assign_pointer_to_connection",
        "pointer_address": pointer_address,
        "connection_id": connection_id
    }
    assign_result = client.invoke(assign_pointer_query)
    print("\n--- Assignment Result ---")
    print(json.dumps(assign_result, indent=2))
```

Run the script again. This creates a connection within your domain and assigns the pointer to it, granting your app permission.

## Step 5: Securely Access the Data

The setup is complete! Your application can now securely read the data from `my_data.json` without knowing its location.

Modify `example_client.py` one last time. The action is now `invoke_through_connection`.

```python
# In example_client.py

# ... (inside if __name__ == '__main__':)

connection_id = "conn_..." # Paste the Connection ID from the previous step's output
pointer_address = "ptr_..." # Paste the Pointer Address from Step 3

access_data_query = {
    "action": "invoke_through_connection",
    "connection_id": connection_id,
    "pointer_address": pointer_address
}

result = client.invoke(access_data_query)

print("\n--- Secure Data Payload ---")
print(json.dumps(result, indent=2))
```

Run the script. The output will show a successful invocation, and the `data` field will contain the contents of your `my_data.json` file!

## Conclusion

Congratulations! You have successfully used the Butterfly System as a secure middleware. Your application (`my-app`) asked for data using an abstract pointer address (`ptr_...`) through a permissioned connection (`conn_...`). The Butterfly System verified the permissions and securely returned the data, completely decoupling your application from the physical location of the datastore.