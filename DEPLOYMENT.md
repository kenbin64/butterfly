# Deployment Bundles and Strategies

The Butterfly System is designed to be flexible, catering to different deployment needs. To clarify these deployment paths, the project is conceptually organized into two "bundles": the **Single-Use Bundle** and the **Pro Bundle**.

These are not separate downloads but rather two documented methods for deploying the same codebase, configured differently to suit the use case.

---

## 1. Single-Use Bundle (Community Edition)

This bundle is designed for the individual developer, researcher, or hobbyist who wants to run a private, self-contained instance of the Butterfly System on their own machine.

*   **Core Philosophy**: To empower individuals with a powerful middleware tool for their personal projects, promoting a decentralized network where each user owns their instance.
*   **What It Is**: A local deployment of the Butterfly System running in `COMMUNITY` mode.
*   **Features**: Includes the core server and all predefined API connections that do not require an API key.
*   **How to Deploy**:
    1.  Follow the setup instructions in the main `README.md`.
    2.  Run the server directly: `python app.py`.
    3.  Or, use Docker Compose with the default `BUTTERFLY_EDITION=COMMUNITY` setting in your `.env` file.

This bundle is perfect for connecting your local applications, data files, and personal cloud services in a secure, private environment.

---

## 2. Pro Bundle (Hosted Edition)

This bundle is designed for deployment on a central server or Virtual Private Server (VPS). It's intended for users who want to provide a shared, managed Butterfly instance for a team, a company, or as part of a larger software-as-a-service offering.

*   **Core Philosophy**: To provide a robust, centralized middleware service that can act as the connective tissue for multiple applications and users.
*   **What It Is**: A server deployment of the Butterfly System running in `HOSTED` mode.
*   **Features**: Includes all features of the Community Edition, plus additional predefined API connections that may require API keys (e.g., paid services, specific enterprise APIs).
*   **How to Deploy**:
    1.  Follow the Docker Compose setup instructions in the main `README.md`.
    2.  In your `.env` file, set `BUTTERFLY_EDITION=HOSTED`.
    3.  Run `docker-compose up --build -d`.

This bundle is ideal for creating a stable, long-running service that multiple client applications can rely on.