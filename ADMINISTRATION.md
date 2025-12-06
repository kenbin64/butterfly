# Administration: Domains and Connections

The Butterfly System provides a simple but powerful administrative layer to help you organize and secure your pointers. This is managed through two core concepts: **Domains** and **Connections**.

This administrative model is not a visual UI but a set of rules and commands enforced by the system, primarily managed via the Admin Command-Line Interface (CLI).

## Core Concepts

### 1. Domains

A **Domain** is a top-level container that belongs to a specific application. Think of it as a project, a workspace, or a namespace for your connections.

*   **Ownership**: Every Domain is owned by an `app_id`, which is derived from the JWT used to make authenticated API requests. This means only the application that created a domain can manage it.
*   **Purpose**: Domains are used to group related **Connections**. For example, you might have a "Personal Data" domain and a "Public APIs" domain, each containing different sets of connections.

### 2. Connections

A **Connection** is a permissioned gateway that lives inside a Domain. It's the "friendly handshake" that grants an application access to a specific set of pointers.

*   **Purpose**: A Connection acts as a logical grouping for pointers. An application cannot invoke a pointer directly; it must do so *through* a connection that the pointer has been assigned to.
*   **Security**: This model ensures that even if an application has a valid JWT, it can only access pointers explicitly assigned to one of its connections. If a pointer has no connection, it is inaccessible via the API.

This two-tiered system allows for fine-grained access control. An application (`app_id`) owns a Domain, and that Domain contains multiple Connections, each providing a gateway to a distinct subset of pointers.

---

## The Admin CLI

The primary way to manage your domains and connections is through the command-line interface (CLI) built into `app.py`.

### Creating a Domain

Before you can create connections or assign pointers, you need a domain. This command creates a new domain owned by a specific `app_id`.

```bash
# Usage: python app.py --create-domain <your_app_id> "<Your Domain Name>"
python app.py --create-domain my-app "My Project Domain"
```
*   Replace `my-app` with the `app_id` you will use in your client's JWT.
*   The command will output the new Domain's ID (e.g., `dom_...`). You will need this ID for the next steps.

### Creating a Pre-defined API Connection

Once you have a Domain, you can create Connections inside it. The easiest way to start is by creating a connection to one of the system's pre-defined public APIs.

```bash
# Usage: python app.py --create-api-connection <domain_id> "<Connection Name>" <api_type>
python app.py --create-api-connection dom_abc123 "Weather Data" weather
```
*   Replace `dom_abc123` with the ID of the domain you just created.
*   This command automatically creates both a `Connection` and a `Pointer` for the weather API and assigns the pointer to the new connection.

*   **Note**: You can get a full list of available `api_type` values for your server's edition by using the `get_available_apis` action via the `/invoke` endpoint.

 ### Listing Your Domains

You can verify which domains are owned by your application.

```bash
python app.py --list-domains my-app
```

After creating connections and assigning pointers, you can use the `get_admin_overview` action via the `/invoke` API endpoint to see a full tree of your domains, connections, and associated pointers.