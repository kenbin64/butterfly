# High-Level System Architecture

This document provides a high-level overview of the major components of the Butterfly System and how they interact, based on the core principles outlined in `PHILOSOPHY.md`.

The system is designed as a decentralized, secure middleware that connects applications to datastores without holding the data itself.

---

## Core Components

The architecture can be understood as three primary components working in concert:

1.  **Flask API Server**: This is the system's front door. All interactions, from creating pointers to invoking them, happen through this RESTful API. It is responsible for:
    *   Handling incoming requests.
    *   Enforcing security through JWT-based authentication.
    *   Orchestrating the other components to fulfill a request.

2.  **Internal Database (SQLite)**: This is the system's "memory" or "map." It does not store any external data. Instead, it stores the definitions and metadata of the system's own structure, including:
    *   All `Pointers` and their `data_reference` targets.
    *   All `Connections` and `Domains` that define access policies.
    *   Tags and other metadata associated with pointers.

3.  **The Pointer Graph**: This is the conceptual heart of the system. It is not a single object but an emergent network formed by all the pointers and their relationships. Its structure is not stored directly but is calculated mathematically.

---

## Architectural Flow and Key Processes

The system's elegance comes from how its components use its core philosophies to operate.

### 1. System Startup: The Bootstrap Process

This process embodies the **"Dynamic Configuration"** principle.

1.  The Flask API server starts.
2.  It uses the one and only hard-coded pointer—the **Genesis Pointer**—to establish a connection to its own Internal Database.
3.  It invokes the Genesis Pointer to read its entire configuration: all domains, connections, and pointers.
4.  With this data loaded, the system is now "self-aware" and ready to accept external requests.

### 2. Relationship Discovery: The Gyroid Engine

This process embodies the **"Gyroid"** and **"Local Awareness"** principles.

When a query requires understanding pointer relationships, the system does not look up a master list. Instead, a dedicated mathematical module (the "Gyroid Engine") performs the following:

1.  It takes a pointer's address as input.
2.  It uses the `_gyroid_equation` to mathematically calculate the addresses of that pointer's "natural neighbors" in the conceptual graph.
3.  This calculation is deterministic and happens on-the-fly, eliminating the need for a central registry and ensuring knowledge remains decentralized.

### 3. A Typical Query: The Invocation Flow

This flow shows how the components work together to securely access data.

```
  Client App         Butterfly API Server         Pointer Graph        External Datastore
      |                    |                           |                      |
      |--- Invoke(JWT) --->|                           |                      |
      |                    |-- Verify JWT & Perms -----|                      |
      |                    |                           |                      |
      |                    |---- Get Pointer ----------->                      |
      |                    |      (from DB)            |                      |
      |                    |                           |                      |
      |                    |<---- Pointer Ref ---------|                      |
      |                    |                           |                      |
      |                    |--- Establish Connection ----------------------->|
      |                    |                           |                      |
      |                    |<---- Data Payload ------------------------------|
      |                    |                           |                      |
      |<-- Encrypted Data--|                           |                      |
      |                    |                           |                      |
 ```
 
 1.  A client application sends an `invoke` request with a JWT to the API server.
 2.  The server authenticates the token and verifies that the application has permission to use the requested pointer through its assigned **Connection**.
 3.  The server retrieves the pointer's definition from the Internal Database.
 4.  The server uses the pointer's `data_reference` to establish a direct, secure connection to the external datastore.
 5.  The datastore returns the requested data directly to the server.
 6.  The server encrypts the payload and returns it to the client application.
 
 ---
 
 ## Deployment Topology for VPS
 
 To prepare for deployment on a VPS, the backend and frontend components are distinctly separated.
 
 *   **Backend (The API Server)**: The Flask application is the backend. In a production environment on your VPS, it should not be run using the development server (`python app.py`). Instead, it should be served by a production-grade WSGI server like **Gunicorn** or **uWSGI**.
 
 *   **Reverse Proxy (Nginx)**: The WSGI server should be placed behind a reverse proxy like **Nginx**. The reverse proxy will handle incoming HTTPS traffic, manage SSL/TLS termination, and forward requests to the Gunicorn process. This is critical for security and performance.
 
 *   **Frontend (The Client App)**: The frontend is any application that makes requests to your API. It can be a web app, a script, or another service and can be hosted anywhere.
 
 ### Production Invocation Flow
 
 This diagram illustrates the separated architecture on a VPS:
 
 ```
  Client App         Internet         VPS Environment
 (Anywhere)                             |
      |                    |             |
      |--- HTTPS Request ->|-------------|--> [ Nginx (Reverse Proxy) ]
      |                    |             |           |
      |                    |             |           | (Forwards Request)
      |                    |             |           |
      |                    |             |           v
      |                    |             |    [ Gunicorn (WSGI Server) ] -> [ Flask App ]
      |                    |             |           ^                            |
      |                    |             |           | (Response)                 | (Handles Logic)
      |                    |             |           |                            v
      |<-- HTTPS Response--|-------------|----[ Nginx ] <-------------------- [ Gunicorn ]
      |                    |             |
 ```
```

1.  A client application sends an `invoke` request with a JWT to the API server.
2.  The server authenticates the token and verifies that the application has permission to use the requested pointer through its assigned **Connection**.
3.  The server retrieves the pointer's definition from the Internal Database.
4.  The server uses the pointer's `data_reference` to establish a direct, secure connection to the external datastore.
5.  The datastore returns the requested data directly to the server.
6.  The server encrypts the payload and returns it to the client application.