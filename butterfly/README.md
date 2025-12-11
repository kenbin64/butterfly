# The Butterfly Ecosystem

This repository contains the core library for the Butterfly Paradigm and a collection of standalone applications built using it.

## The Core Paradigm

The "search engine" of the ecosystem is the core framework located in the `/core` directory. This library provides the fundamental components of the Butterfly Paradigm:

*   **`QubeResolver`**: The authorization gatekeeper that resolves `z`-addresses.
*   **`QubeIndex`**: The "card catalog" for discovering `z`-addresses.
*   **Storage Adapters**: Pluggable modules for connecting to different persistence layers (e.g., SQLite, PostgreSQL).

All applications in this ecosystem are "Butterfly Compliant"—they are built by importing and using this core framework.

## Applications

Each application resides in its own folder under `/apps`. They are all standalone and demonstrate different use cases of the paradigm.

### 1. Stock Tracker (`/apps/stock_tracker`)

A command-line tool to fetch financial data for a given stock ticker. It demonstrates how the paradigm can securely connect to external APIs.

**To Run:**
```shell
# Set the required environment variables
export APP_CONFIG_PATH="./config.yaml"
export APP_PUBLIC_KEY_PATH="./public_key.pem"

# Run the tracker for a specific stock ticker
node apps/stock_tracker/tracker.js AAPL
```

### 2. Game Arena (`/apps/game_arena`)

A turn-based RPG simulation that demonstrates complex state management and performance benchmarking.

**To Run:**
```shell
# Set the required environment variables
export APP_CONFIG_PATH="./config.yaml"
export APP_PUBLIC_KEY_PATH="./public_key.pem"

# Run the simulation for a specific number of turns
node apps/game_arena/simulation.js 10
```

## Setup

Before running any application, ensure the environment is set up correctly.

1.  **Install Dependencies:**
    ```shell
    npm install sqlite3 js-yaml pg pidusage node-fetch
    ```

2.  **Generate Keys and Signature (One-time setup):**
    ```shell
    openssl genpkey -algorithm ED25519 -out private_key.pem
    openssl pkey -in private_key.pem -pubout -out public_key.pem
    openssl dgst -sha256 -sign private_key.pem -out config.yaml.sig config.yaml
    ```

This structure allows for the independent development of many applications, all sharing the same secure, powerful, and decoupled core.