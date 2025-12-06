# Policy Injection and Management

In the Butterfly System, a "policy" is not a distinct object you create. Instead, policies are an emergent property of the system's structure. A policy is defined by how you organize your pointers, connections, and domains. "Policy Injection" is the act of applying these structural rules.

This document explains the three conceptual levels of policy management.

---

## The Principle of Inherited Policy

The Butterfly System is designed to be a respectful guest within any existing digital ecosystem. It does not impose its own will. Instead, it defaults to a principle of maximum caution:

*   **Adoption of Native Policies**: The system will, by default, adopt the policies of the native systems it connects to.
*   **Default to Most Restrictive**: When a pointer provides access to multiple systems, or when no specific internal policy is defined, the Butterfly System's effective policy for that interaction defaults to the **most restrictive policy** of any system being accessed. For example, if one connected system is read-only, the entire interaction through that pointer chain becomes read-only, unless a more granular internal policy explicitly allows otherwise for a different path.

The policy injection methods described below are ways to define *more granular, specific rules* within the Butterfly System itself, which build upon this secure foundation.

---

## 1. Single-Domain Policy Injection (Standard Access Control)

This is the most common and fundamental form of policy enforcement in the system. It governs what a specific application (`app_id`) can access within its own domains.

**How it works:**
The policy is defined by the **assignments** between pointers and connections.

1.  An application authenticates with its `app_id`.
2.  The system grants it access only to the **Domains** it owns.
3.  Within those domains, the application can only "see" and invoke pointers through the **Connections** it has access to.

**Injecting the Policy:**
A domain owner "injects" a policy by deciding which pointers get assigned to which connections.

*   **Example**: You have a domain with two connections: `Public Data` and `Private Credentials`.
    *   You assign your public API pointers (like `weather`, `news`) to the `Public Data` connection.
    *   You assign your encrypted cloud secret pointers to the `Private Credentials` connection.

Your application's policy is now injected: one part of your app might only use the `Public Data` connection, while a secure backend service uses the `Private Credentials` connection. This is the core security model of the system.

---

## 2. Multi-Domain Policy Injection (Federated Model)

This applies when you need to enforce a consistent policy across multiple independent domains, potentially owned by different applications or even running on different servers. This is achieved using the **Federation** model.

**How it works:**
You create a central "Policy Instance" of the Butterfly System. This instance holds pointers that represent rules.

*   **Example**: You run a central "Compliance" instance. It has a pointer whose `data_reference` contains a JSON object: `{"rule": "data_must_be_encrypted", "status": "active"}`.

**Injecting the Policy:**
Other Butterfly instances or domains connect to this central "Compliance" instance as if it were any other external API.

1.  An application within `Domain A` invokes a pointer that is connected to the "Compliance" instance.
2.  It retrieves the policy (`{"rule": "data_must_be_encrypted", ...}`).
3.  The application can now use this information to alter its behavior, enforcing the policy.

This is a **pull-based** model where domains opt-in to a shared policy by connecting to a central policy server.

---

## 3. Admin Policy Injection (Direct Data Layer Intervention)

This is the highest level of policy enforcement, available only to the system administrator—the person with direct access to the server and its database. This is a **push-based** model where the admin can enforce system-wide rules.

**How it works:**
The administrator bypasses the API and interacts directly with the database (`butterfly_local.db` or equivalent) using scripts or other tools.

**Injecting the Policy:**
The admin can perform mass operations that are not exposed via the standard API.

*   **Example 1 (Tagging)**: An admin discovers a data source is unreliable. They can run a script to find all pointers pointing to that source and programmatically add an `"untrusted"` tag to all of them.
    ```sql
    UPDATE pointers SET tags = json_insert(tags, '$[#]', 'untrusted') WHERE data_reference LIKE '%unreliable-api.com%';
    ```
*   **Example 2 (Quarantine)**: An admin can create a special "quarantine" connection that has no domains associated with it. They can then re-assign all pointers from a problematic source to this connection, effectively making them inaccessible to all applications via the API until the issue is resolved.

This level of control is for global system maintenance and security intervention and is intentionally kept separate from the application-level API.