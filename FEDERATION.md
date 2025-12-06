# Federation: Connecting Multiple Butterfly Instances

The Butterfly System is designed for decentralized, organic growth. A powerful expression of this is "federation"—connecting multiple, independent Butterfly instances running on different servers into a larger, interconnected network.

This is achieved not by special server-to-server configurations, but by using the system's own core concepts: **Pointers** and **Connections**.

## The Core Concept

From the perspective of `Instance A`, a separate `Instance B` is just another external data source. You create a connection to it just like you would for any other API. The "friendly handshake" is established by securely sharing the necessary credentials (JWT and encryption keys) between the instance administrators.

When a pointer on `Instance A` is invoked, it can trigger a secure, encrypted API call to `Instance B`, which then performs an action and returns the result. This allows you to chain invocations across a distributed network.

---

## Step-by-Step Guide to Connecting Two Instances

Let's say we have two servers:
*   **Instance A**: Running at `https://instance-a.com`
*   **Instance B**: Running at `https://instance-b.com`

Our goal is to allow `Instance A` to securely query a pointer that exists on `Instance B`.

### Step 1: On `Instance B` (The "Remote" Server)

The administrator of `Instance B` must treat `Instance A` as a trusted client application.

1.  **Generate Credentials**: The admin of `Instance B` needs to generate a set of credentials specifically for `Instance A` to use. This includes:
    *   A unique `app_id` (e.g., `instance-a-federation-client`).
    *   The `JWT_SECRET_KEY` from `Instance B`'s environment.
    *   The `BUTTERFLY_ENCRYPTION_KEY` from `Instance B`'s environment.

2.  **Securely Share Credentials**: These three pieces of information must be securely transmitted to the administrator of `Instance A`. This is the manual "handshake" that establishes trust between the two systems.

### Step 2: On `Instance A` (The "Local" Server)

The administrator of `Instance A` now configures a pointer that represents a query into `Instance B`.

1.  **Create a "Circuit" Pointer**: The admin will create a new pointer on `Instance A`. The `data_reference` of this pointer will be a special `internal_circuit`. This circuit contains the encrypted query that `Instance B` will execute.

2.  **Use a Helper Script**: The easiest way to construct this is with a helper script or by adapting `example_client.py`. You need to use the keys from `Instance B` to encrypt the query for `Instance B`.

    *   **Query for Instance B**: This is the action you want `Instance B` to perform.
        ```json
        {
            "action": "get_pointer_summary",
            "pointer_address": "ptr_abc123_on_instance_b"
        }
        ```

    *   **Encrypt with B's Keys**: Use the `BUTTERFLY_ENCRYPTION_KEY` from `Instance B` to encrypt the above JSON query. Let's say the result is `encrypted_query_for_b`.

3.  **Create the Pointer on Instance A**: Now, create the pointer on `Instance A` that will trigger this federated call.

    *   **Action**: `create_pointer`
    *   **Description**: "Federated query for Pointer Summary on Instance B"
    *   **`data_reference`**: This is the crucial part. It points to `Instance B`'s invoke endpoint and includes the encrypted payload.
        ```
        https://instance-b.com/invoke
        ```
        *(Note: For a POST request with a body, the pointer's `data_reference` should point to the endpoint, and the client application would construct the final request body).*

    A more advanced pattern is to use the `internal_circuit` feature. You would create a pointer on `Instance A` whose `data_reference` is literally the encrypted query for `Instance B`. A client of `Instance A` would then invoke this pointer and use its result to call `Instance B`.

### Step 3: Making the Federated Call

A client application connected to `Instance A` can now invoke the federated pointer.

1.  The client invokes the pointer on `Instance A`.
2.  `Instance A` returns the `data_reference`, which is `https://instance-b.com/invoke`.
3.  The client application now knows the endpoint for `Instance B`. It also has the pre-encrypted payload (`encrypted_query_for_b`).
4.  The client constructs a `POST` request to `https://instance-b.com/invoke`:
    *   It uses the `JWT_SECRET_KEY` from `Instance B` to generate a valid `Bearer` token.
    *   The body of the request is the `encrypted_query_for_b`.
5.  `Instance B` receives the request, authenticates it, decrypts the payload, executes the query (`get_pointer_summary`), and returns an encrypted response.
6.  The client decrypts the response from `Instance B` using `Instance B`'s encryption key.

This architecture maintains the zero-trust and encrypted-by-default nature of the system. Each instance is responsible for its own security, and connections are explicit, permissioned, and secure.