import json
import os
import textwrap
from cryptography.fernet import Fernet

# Define provider-specific details
PROVIDERS = {
    "aws": {
        "name": "Amazon Web Services (AWS)",
        "console_url": "https://console.aws.amazon.com/iam/home?#/security_credentials",
        "docs_url": "https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys",
        "instructions": "Create an IAM user with programmatic access to get an Access Key ID and Secret Access Key."
    },
    "gcp": {
        "name": "Google Cloud Platform (GCP)",
        "console_url": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "docs_url": "https://cloud.google.com/iam/docs/creating-managing-service-account-keys",
        "instructions": "Create a Service Account and download its JSON key file."
    },
    "azure": {
        "name": "Microsoft Azure",
        "console_url": "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
        "docs_url": "https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal",
        "instructions": "Create an App Registration (Service Principal) and get its Application (client) ID, a Client Secret, and your Directory (tenant) ID."
    }
}

def print_header():
    """Prints the script's header."""
    print("=" * 60)
    print(" Butterfly System - Cloud Connection Setup Helper")
    print("=" * 60)
    print("This script guides you through creating a secure pointer for your")
    print("cloud provider credentials within your Butterfly instance.")
    print("-" * 60)

def select_provider():
    """Lets the user select a cloud provider."""
    print("\n[1] Select a cloud provider to configure:")
    for i, key in enumerate(PROVIDERS.keys()):
        print(f"  {i+1}. {PROVIDERS[key]['name']}")

    while True:
        try:
            choice = int(input("Enter your choice: ")) - 1
            if 0 <= choice < len(PROVIDERS):
                return list(PROVIDERS.keys())[choice]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")

def get_credentials_and_generate_pointer(provider_key):
    """Guides the user, gets credentials, and generates the pointer config."""
    provider = PROVIDERS[provider_key]
    credentials = {"provider": provider_key}

    print(f"\n[2] Go to the {provider['name']} console to get your credentials:")
    print(f"    - Console URL: {provider['console_url']}")
    print(f"    - Instructions: {provider['instructions']}")

    print(f"\n[3] Enter the credentials you received from {provider['name']}:")

    if provider_key == "aws":
        credentials["access_key_id"] = input("    Enter your Access Key ID: ").strip()
        credentials["secret_access_key"] = input("    Enter your Secret Access Key: ").strip()
    elif provider_key == "azure":
        credentials["client_id"] = input("    Enter your Application (client) ID: ").strip()
        credentials["client_secret"] = input("    Enter your Client Secret: ").strip()
        credentials["tenant_id"] = input("    Enter your Directory (tenant) ID: ").strip()
    elif provider_key == "gcp":
        key_path = input("    Enter the full path to your Service Account JSON key file: ").strip()
        try:
            with open(key_path, 'r') as f:
                # For GCP, the entire key file content is the credential
                credentials["service_account_json"] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"\n[!] ERROR: Could not read or parse the JSON file at '{key_path}'. {e}")
            return

    # Validate that credentials were entered
    if all(not v for k, v in credentials.items() if k != "provider"):
        print("\n[!] No credentials were entered. Aborting.")
        return

    # Load the encryption key from the environment to encrypt the secrets
    encryption_key_str = os.environ.get('BUTTERFLY_ENCRYPTION_KEY')
    if not encryption_key_str:
        print("\n[!] ERROR: The 'BUTTERFLY_ENCRYPTION_KEY' environment variable is not set.")
        print("    This key is required to encrypt your secrets. Please set it and run the script again.")
        return

    fernet = Fernet(encryption_key_str.encode())
    encrypted_config = fernet.encrypt(json.dumps(credentials).encode()).decode()

    print("\n" + "=" * 60)
    print(" Success! Your cloud credentials have been securely encrypted.")
    print("=" * 60)
    print("\n[4] To add this to your Butterfly instance, use the 'create_pointer' action.")
    print("    Below is the JSON payload for your request. You can use this with")
    print("    the 'example_client.py' script or your own application.")

    pointer_payload = {
        "action": "create_pointer",
        "description": f"Cloud Credentials for {provider['name']}",
        "data_reference": encrypted_config,
        "tags": ["cloud_credentials", provider_key]
    }

    # Use textwrap to format the JSON nicely
    formatted_json = textwrap.indent(json.dumps(pointer_payload, indent=4), '    ')
    print("\n--- JSON Payload for create_pointer ---\n")
    print(formatted_json)
    print("\n---------------------------------------\n")
    print("After creating this pointer, your applications can invoke it through a")
    print("connection to securely retrieve these credentials for use with cloud SDKs.")


if __name__ == '__main__':
    print_header()
    try:
        selected_provider = select_provider()
        get_credentials_and_generate_pointer(selected_provider)
    except (KeyboardInterrupt, EOFError):
        print("\n\nSetup cancelled. Exiting.")

```

### 2. `README.md` Update

I'll update your `README.md` to include a section for this new helper script, making it easy for users to discover.

```diff
--- a/c:\Projects\repo\condiut\butterfly\README.md
+++ b/c:\Projects\repo\condiut\butterfly\README.md
@@ -161,3 +161,19 @@
 
 The client will authenticate, send an encrypted request to get graph stats, and print the decrypted response.
 
+### Setting Up Cloud & Social Logins
+
+The Butterfly System can be used to securely store and manage credentials for cloud providers and OAuth social logins. The project includes helper scripts to guide you through this process.
+
+These scripts will:
+1.  Provide you with links to the developer consoles where you can obtain API keys.
+2.  Prompt you for your secrets (e.g., Client ID, Access Keys).
+3.  Generate a secure, encrypted `data_reference` and the JSON payload needed to create a pointer for your configuration.
+
+To configure **OAuth for social logins** (Google, GitHub):
+```bash
+python setup_oauth_helper.py
+```
+
+To configure **cloud provider credentials** (AWS, GCP, Azure):
+```bash
+python setup_cloud_helper.py
+```

```

These additions provide a clear, secure, and user-empowering path for integrating with major cloud services, reinforcing the Butterfly System's role as a powerful and flexible middleware.

<!--
[PROMPT_SUGGESTION]How can I set up a `docker-compose.yml` file to manage the application and a database?[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]How can I set up automated testing for the API endpoints using GitHub Actions?[/PROMPT_SUGGESTION]
-->