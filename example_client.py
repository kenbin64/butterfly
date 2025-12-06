import requests
import jwt
import json
import os
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet


class ButterflyClient:
    """
    An example client for demonstrating how to interact with the Butterfly System API.
    """

    def __init__(self, base_url, app_id, jwt_secret, encryption_key):
        if not all([base_url, app_id, jwt_secret, encryption_key]):
            raise ValueError("All initialization parameters are required.")
        self.base_url = base_url
        self.app_id = app_id
        self.jwt_secret = jwt_secret
        self.fernet = Fernet(encryption_key)

    def _generate_token(self):
        """Generates a JWT token for the configured app_id."""
        payload = {
            'app_id': self.app_id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        print(f"[*] Generated JWT for app_id: {self.app_id}")
        return token

    def encrypt_query(self, query: dict) -> str:
        """Encrypts a query dictionary into a secure string."""
        json_string = json.dumps(query)
        encrypted_message = self.fernet.encrypt(json_string.encode('utf-8'))
        return encrypted_message.decode('utf-8')

    def decrypt_response(self, encrypted_str: str) -> dict:
        """Decrypts a secure response string back into a dictionary."""
        decrypted_message = self.fernet.decrypt(encrypted_str.encode('utf-8'))
        return json.loads(decrypted_message.decode('utf-8'))

    def invoke(self, query: dict):
        """
        Authenticates, encrypts, and sends a query to the /invoke endpoint,
        then decrypts and returns the response.
        """
        token = self._generate_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'text/plain'
        }

        print(f"\n[*] Encrypting query: {query}")
        encrypted_query = self.encrypt_query(query)

        print(f"[*] Sending encrypted request to {self.base_url}/invoke")
        try:
            response = requests.post(f"{self.base_url}/invoke", data=encrypted_query, headers=headers, timeout=10)
            response.raise_for_status()

            print("[*] Received encrypted response. Decrypting...")
            decrypted_response = self.decrypt_response(response.text)
            return decrypted_response

        except requests.exceptions.RequestException as e:
            print(f"[!] Request failed: {e}")
            return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # --- Configuration ---
    # IMPORTANT: These should be loaded securely, e.g., from environment variables.
    # For the server and client to communicate, they MUST use the same keys.
    JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'default-super-secret-key-for-dev')
    ENCRYPTION_KEY = os.environ.get('BUTTERFLY_ENCRYPTION_KEY')

    if not ENCRYPTION_KEY:
        raise ValueError("The BUTTERFLY_ENCRYPTION_KEY environment variable must be set.")

    client = ButterflyClient("http://localhost:5001", "my-test-app", JWT_SECRET, ENCRYPTION_KEY.encode())

    # --- Example Invocation ---
    example_query = {"action": "get_graph_stats"}
    result = client.invoke(example_query)

    print("\n--- Decrypted Response ---")
    print(json.dumps(result, indent=2))