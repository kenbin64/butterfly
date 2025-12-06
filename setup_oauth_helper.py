import json
import os
import textwrap
from cryptography.fernet import Fernet


PROVIDERS = {
    "google": {
        "name": "Google",
        "console_url": "https://console.developers.google.com/apis/credentials",
        "docs_url": "https://developers.google.com/identity/protocols/oauth2",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["openid", "profile", "email"]
    },
    "github": {
        "name": "GitHub",
        "console_url": "https://github.com/settings/developers",
        "docs_url": "https://docs.github.com/en/developers/apps/building-oauth-apps",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": ["read:user", "user:email"]
    },
    "microsoft": {
        "name": "Microsoft",
        "console_url": "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
        "docs_url": "https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": ["User.Read"]
    }
}

def print_header():
    """Prints the script's header."""
    print("=" * 60)
    print(" Butterfly System - OAuth Connection Setup Helper")
    print("=" * 60)
    print("This script guides you through creating a secure OAuth configuration")
    print("pointer within your Butterfly instance. It does NOT handle the")
    print("actual login flow but helps you store your credentials securely.")
    print("-" * 60)

def select_provider():
    """Lets the user select an OAuth provider."""
    print("\n[1] Select an OAuth provider to configure:")
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

    print(f"\n[2] Go to the {provider['name']} Developer Console to get your credentials:")
    print(f"    - Console URL: {provider['console_url']}")
    print(f"    - Documentation: {provider['docs_url']}")
    print("\n    When creating your credentials, you will be asked for a 'Redirect URI'.")
    print("    This URI is part of YOUR client application that will use Butterfly.")
    print("    A common example for local development is: http://localhost:3000/callback")

    print(f"\n[3] Enter the credentials you received from {provider['name']}:")
    client_id = input("    Enter your Client ID: ").strip()
    client_secret = input("    Enter your Client Secret: ").strip()

    if not client_id or not client_secret:
        print("\n[!] Client ID and Client Secret cannot be empty. Aborting.")
        return

    # Load the encryption key from the environment to encrypt the secrets
    encryption_key_str = os.environ.get('BUTTERFLY_ENCRYPTION_KEY')
    if not encryption_key_str:
        print("\n[!] ERROR: The 'BUTTERFLY_ENCRYPTION_KEY' environment variable is not set.")
        print("    This key is required to encrypt your secrets. Please set it and run the script again.")
        return

    fernet = Fernet(encryption_key_str.encode())

    # This is the sensitive data that will be encrypted
    oauth_config = {
        "provider": provider_key,
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_url": provider['auth_url'],
        "token_url": provider['token_url'],
        "scopes": provider['scopes']
    }

    encrypted_config = fernet.encrypt(json.dumps(oauth_config).encode()).decode()

    print("\n" + "=" * 60)
    print(" Success! Your OAuth configuration has been securely encrypted.")
    print("=" * 60)
    print("\n[4] To add this to your Butterfly instance, use the 'create_pointer' action.")
    print("    Below is the JSON payload for your request. You can use this with")
    print("    the 'example_client.py' script or your own application.")

    pointer_payload = {
        "action": "create_pointer",
        "description": f"OAuth Configuration for {provider['name']}",
        "data_reference": encrypted_config,
        "tags": ["oauth_config", provider_key]
    }

    # Use textwrap to format the JSON nicely
    formatted_json = textwrap.indent(json.dumps(pointer_payload, indent=4), '    ')
    print("\n--- JSON Payload for create_pointer ---\n")
    print(formatted_json)
    print("\n---------------------------------------\n")
    print("After creating this pointer, your applications can invoke it through a")
    print("connection to securely retrieve the OAuth configuration without ever")
    print("exposing the client_secret directly.")


if __name__ == '__main__':
    print_header()
    try:
        selected_provider = select_provider()
        get_credentials_and_generate_pointer(selected_provider)
    except (KeyboardInterrupt, EOFError):
        print("\n\nSetup cancelled. Exiting.")

```

### 2. `README.md` Update

To make this new tool discoverable, I'll add a section to your `README.md` that explains its purpose and how to use it.

```diff