# Butterfly System

The Butterfly System is **middleware**—not an application or a datastore in itself. Its core purpose is to make and secure all connections between your various systems. It functions like a library card catalog for your data; it holds encrypted pointers that tell you where information is, but it never touches the information itself.

Once a pointer facilitates a secure connection, the system can then use its advanced mathematical features (like logic gates, determination graphs, and decision trees) to work directly with the data returned from that connection.

This system is designed as a controlled growth system, meant to grow to the *n*th degree as far as resources allow. It uses principles like the Golden Ratio and gyroid structures to maximize area strength while minimizing material, ensuring it grows like a flower, not a weed. It connects apps, datastores, cloud services, AI, and local files through a pointer-based architecture where interactions are primarily read-only.

The system is built on several core principles:
- **Pointer Graph**: A network where nodes (pointers) are self-contained, encrypted entities that exist only within the system. They are references, not containers; they never touch or hold the data they point to.
- **Organic Growth**: The system is designed to evolve uniquely for each user; once new connections are made, no two systems will be the same.
- **Zero-Trust Architecture**: Interactions are enforced through cryptographic handshakes between verified connections, ensuring no pointer can be invoked without explicit permission.
- **Mathematical Foundation**: Uses a "Gyroid" equation to deterministically discover and score relationships between pointers based on their unique addresses.
- **Encrypted Communication**: All client-server payloads are encrypted to simulate end-to-end security.

## Guiding Principles and Disclaimers

The Butterfly System is governed by a set of inherent, mathematical, and philosophical principles. Before using the system, it is important to understand its nature and the responsibilities of the user.

- **[The Philosophical and Mathematical Foundations](./docs/PHILOSOPHY.md)**: An explanation of the core concepts of the Golden Ratio, Fibonacci Spiral, and Gyroid structures that govern the system's design.
- **[What It Does and Does Not Do](./DOS_AND_DONTS.md)**: A clear disclaimer on the system's capabilities and limitations.
- **[Terms of Service & Acknowledgment of Principles](./TERMS_OF_SERVICE.md)**: An acknowledgment of the foundational laws governing the system's environment.

## License

The Butterfly System core is released under a permissive, attribution-based license. It can be used for any purpose, commercial or private, provided that attribution is given.

Please see the **[LICENSE](./LICENSE)** file for the full terms and specific attribution requirements.

## Support and Liability

This project is provided without any form of customer service. However, users are encouraged to submit bug reports. Patches for reported bugs may be provided via a mailing list for updates.

**The creator and distributor of the Butterfly System assume no liability.** Each running instance of the software is the sole responsibility of its owner. The owner is responsible for all connections made and must ensure they have the necessary licenses and permissions to connect to any given app, data store, or service.

While the system has internal safeguards, the ultimate responsibility for compliance and secure operation rests with the user.

## Security and Policy Model

The Butterfly System's security is built on a model of "policy injection," where access rules are defined by the structure of your domains, connections, and pointers.

By default, the system adopts the most restrictive policy of any system it connects to, ensuring a secure-by-default posture.

For a detailed explanation, please see the **[Policy Injection and Management Guide](./docs/POLICIES.md)**.

## Automated Testing

This project uses GitHub Actions for Continuous Integration (CI). The workflow is defined in `.github/workflows/ci.yml`.

On every push and pull request to the `main` branch, the workflow automatically runs a linter (`flake8`) to enforce code style and a full integration test using `pytest`. It also generates a code coverage report and uploads it to Codecov, ensuring the API is live and code quality is maintained.

## Contributing

We welcome contributions to the Butterfly System! Please read our **[CONTRIBUTING.md](./CONTRIBUTING.md)** for guidelines on how to submit bug reports and feature requests.

## Features

- **Flask API**: A robust API for creating, querying, and managing the pointer graph.
- **SQLite Backend**: A lightweight, file-based database for local logging and data storage.
- **JWT Authentication**: Secure, token-based authentication for all API endpoints.
- **Admin CLI**: A command-line interface for administrative tasks. See the **[Administration Guide](./docs/ADMINISTRATION.md)** for details on managing Domains and Connections.
- **Pre-defined API Connections**: Easily connect to common public APIs for data like weather, news, and more.

## Editions

The Butterfly System is designed to run in two distinct editions, configured via an environment variable.

For a detailed guide on the deployment strategies for these editions, please see the **[Deployment Bundles and Strategies Guide](./docs/DEPLOYMENT.md)**.

### Community Edition (Downloadable)

This is the default version, intended for individual users to run on their own machines. It provides a core set of publicly accessible, key-less API connections out of the box, allowing users to connect their own applications and data sources in a private, self-hosted environment.

*   **Configuration**: No environment variable needed, or set `BUTTERFLY_EDITION=COMMUNITY`.

### Hosted Edition (VPS)

This version is intended for deployment on a central server (like a VPS). It includes all the Community APIs plus additional connections that may require API keys or are specific to the hosted environment.

*   **Configuration**: Set the environment variable `BUTTERFLY_EDITION=HOSTED`.

## Getting Started

### Prerequisites

- Python 3.9+
- `pip` for package management

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd butterfly
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### First-Time Setup

The first time you run the server, a command-line **Setup Wizard** will launch automatically. This wizard will guide you through configuring two key settings:

1.  **Database Location**: Choose between the default local database (`butterfly_local.db`) or specify a custom path for the SQLite file.
2.  **Authentication Mode**:
    *   **Internal (Default)**: The server manages its own secure JWT authentication.
    *   **Passthrough**: The server bypasses authentication, allowing you to use a reverse proxy (like Nginx or Traefik) to handle access control. This is an advanced option for middleware deployments.

Your choices will be saved in a `config.json` file. To run the wizard again, simply delete this file.

### Running the Server

To start the Flask development server for the **Community Edition**, simply run `app.py`:

```bash
python app.py
```

The server will start on `http://0.0.0.0:5001`.