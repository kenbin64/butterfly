# Helper Scripts for Configuration

The Butterfly System includes several standalone Python scripts located in the root of the project directory. These helpers are designed to guide you through securely configuring connections to external services like cloud providers and OAuth identity providers.

**Core Philosophy:** Instead of handling your secret keys directly, these scripts help you encrypt them and package them into a `create_pointer` payload. This allows you to store sensitive configurations as secure pointers within the Butterfly System, which can then be safely invoked by your applications through authorized connections.

**Prerequisite:** Before running any helper script, you must have the `BUTTERFLY_ENCRYPTION_KEY` environment variable set. This is the same key your `app.py` server uses and is required to encrypt your secrets.

```bash
# First, generate a key if you don't have one
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Then, set the environment variable (example for Linux/macOS)
export BUTTERFLY_ENCRYPTION_KEY="your-generated-key-goes-here"
```

---

## 1. OAuth / Social Logins Helper

This script helps you configure pointers for handling social logins with providers like Google, GitHub, and Microsoft.

*   **Script Location:** `setup_oauth_helper.py` (in the project root)
*   **Command:**
    ```bash
    python setup_oauth_helper.py
    ```

### How It Works

1.  **Select a Provider:** The script will ask you to choose an OAuth provider.
2.  **Get Credentials:** It will provide you with a direct link to that provider's developer console where you can create an OAuth application and get a **Client ID** and **Client Secret**.
3.  **Enter Credentials:** You will be prompted to enter the credentials into the script.
4.  **Generate Payload:** The script uses your `BUTTERFLY_ENCRYPTION_KEY` to encrypt your Client Secret and other configuration details. It then prints a complete JSON payload.

### Using the Output

The generated JSON payload is designed to be used with the `create_pointer` action. You can use a tool like the `example_client.py` to send this payload to your running Butterfly instance. This creates a secure pointer that your application can later invoke to get the necessary OAuth configuration without ever exposing the secret key in its own source code.

---

## 2. Cloud Provider Credentials Helper

This script helps you securely store the credentials needed to interact with major cloud providers like AWS, Google Cloud Platform (GCP), and Microsoft Azure.

*   **Script Location:** `setup_cloud_helper.py` (in the project root)
*   **Command:**
    ```bash
    python setup_cloud_helper.py
    ```

### How It Works

1.  **Select a Provider:** The script will ask you to choose a cloud provider.
2.  **Get Credentials:** It will provide instructions and a link to the appropriate console for generating API credentials (e.g., AWS Access Keys, Azure Service Principals, GCP Service Account keys).
3.  **Enter Credentials:** You will be prompted to enter your keys, secrets, or file paths directly into the script.
4.  **Generate Payload:** The script encrypts all sensitive information and prints a complete JSON payload for the `create_pointer` action.

### Using the Output

Similar to the OAuth helper, you can use the generated JSON payload to create a secure pointer in your Butterfly instance. Your applications can then invoke this pointer through a connection to dynamically and securely fetch the credentials needed to initialize a cloud SDK (like `boto3` for AWS or `azure-identity` for Azure). This practice prevents hardcoding secret keys in your application code or configuration files.