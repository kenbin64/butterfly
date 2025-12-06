import requests
import sys
import os
import json
import jwt
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone

# --- Configuration ---
BASE_URL = "http://localhost:5001"
APP_ID = "health-check-app"

def check_liveness(url):
    """
    Performs a basic liveness check by hitting an unauthenticated endpoint.
    Checks if the service is running and responding to HTTP requests.
    """
    print(f"[*] Performing Liveness Check on {url}...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("[+] Liveness Check PASSED: Service is up and responding.")
            return True
        else:
            print(f"[-] Liveness Check FAILED: Service returned status code {response.status_code}.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[-] Liveness Check FAILED: Could not connect to the service. Error: {e}")
        return False

def check_readiness(url, jwt_secret, encryption_key):
    """
    Performs a deep readiness check by making an authenticated, encrypted API call.
    Checks if the service can process a valid request.
    """
    print("\n[*] Performing Readiness Check (API invocation)...")
    if not jwt_secret or not encryption_key:
        print("[-] Readiness Check SKIPPED: JWT_SECRET_KEY or BUTTERFLY_ENCRYPTION_KEY not set.")
        return False

    try:
        fernet = Fernet(encryption_key)

        # 1. Generate Token
        token_payload = {
            'app_id': APP_ID,
            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")

        # 2. Encrypt Query
        query = {"action": "get_graph_stats"}
        encrypted_query = fernet.encrypt(json.dumps(query).encode()).decode()

        # 3. Make Request
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'text/plain'
        }
        response = requests.post(f"{url}/invoke", data=encrypted_query, headers=headers, timeout=10)
        response.raise_for_status()

        # 4. Decrypt and Verify Response
        decrypted_response_data = fernet.decrypt(response.text.encode())
        result = json.loads(decrypted_response_data)

        if result.get("status") == "success":
            print("[+] Readiness Check PASSED: API invocation was successful.")
            return True
        else:
            print(f"[-] Readiness Check FAILED: API returned status '{result.get('status')}'.")
            return False

    except Exception as e:
        print(f"[-] Readiness Check FAILED: An unexpected error occurred. Error: {e}")
        return False

if __name__ == '__main__':
    print("--- Butterfly System Health Check ---")

    # Perform liveness check
    is_live = check_liveness(BASE_URL)

    # Perform readiness check if liveness passed
    is_ready = False
    if is_live:
        jwt_secret_key = os.environ.get('JWT_SECRET_KEY', 'default-super-secret-key-for-dev')
        encryption_key_str = os.environ.get('BUTTERFLY_ENCRYPTION_KEY')
        is_ready = check_readiness(BASE_URL, jwt_secret_key, encryption_key_str.encode() if encryption_key_str else None)

    print("\n--- Summary ---")
    if is_live and is_ready:
        print("✅ Service is healthy.")
        sys.exit(0)
    else:
        print("❌ Service is unhealthy.")
        sys.exit(1)