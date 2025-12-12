from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import hmac
import hashlib
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
import os
import sqlite3
import base64
import requests
from cryptography.fernet import Fernet
import shutil
from functools import wraps
import math
import jwt

# --- DBManager: Abstracting Database Operations ---


class DBManager:
    def __init__(self, db_config: dict):
        self.db_type = db_config.get('type', 'sqlite')
        self.db_path = db_config.get('path', 'butterfly_local.db')
        self.conn = None
        self._connect()

    def _connect(self):
        if self.db_type == 'sqlite':
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        if not self.conn:
            self._connect()
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        if self.conn:
            self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


# --- EncryptionModule: Simulated End-to-End Encryption ---


class EncryptionModule:
    """
    A simple module to simulate end-to-end encryption.
    It uses a basic XOR cipher and Base64 encoding for demonstration.
    This is now upgraded to use Fernet for real symmetric encryption.
    """

    def __init__(self):
        """
        Initializes the encryption module.
        In a real-world scenario, the key MUST be loaded from a secure environment variable.
        """
        key = os.environ.get('BUTTERFLY_ENCRYPTION_KEY')
        if not key:
            print(
                "[!] WARNING: BUTTERFLY_ENCRYPTION_KEY environment variable not set. Generating a temporary key.")
            print(
                "[!] This is INSECURE for production. A new key will be generated on each restart.")
            key = Fernet.generate_key()

        # The key must be URL-safe base64-encoded.
        self.fernet = Fernet(key.encode())

    def encrypt(self, data: dict) -> str:
        """Encrypts a dictionary into a secure message."""
        json_string = json.dumps(data)
        encrypted_message = self.fernet.encrypt(json_string.encode('utf-8'))
        return encrypted_message.decode('utf-8')

    def decrypt(self, encrypted_str: str) -> dict:
        """Decrypts a secure message back into a dictionary."""
        decrypted_message = self.fernet.decrypt(encrypted_str.encode('utf-8'))
        return json.loads(decrypted_message.decode('utf-8'))


# --- AuditModule: Lightweight Local Database Logging ---

class AuditModule:
    def __init__(self, db_config: dict):
        self.db_manager = DBManager(db_config)
        self._initialize_schema()
        print(
            f"[*] AuditModule initialized. Logging to '{self.db_manager.db_path}'.")

    def _initialize_schema(self):
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS audit_log
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             timestamp TEXT NOT NULL,
             action TEXT NOT NULL,
             details TEXT)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS domains
            (id TEXT PRIMARY KEY,
             name TEXT NOT NULL UNIQUE,
             created_at TEXT NOT NULL)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS connections
            (id TEXT PRIMARY KEY,
             name TEXT NOT NULL,
             description TEXT,
             allow_writes INTEGER DEFAULT 0,
             status TEXT NOT NULL DEFAULT 'active', -- 'active', 'disabled'
             domain_id TEXT NOT NULL,
             FOREIGN KEY(domain_id) REFERENCES domains(id))
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS pointers
            (address TEXT PRIMARY KEY, -- This is the resource_id for an SRL
             description TEXT,
             data_reference TEXT NOT NULL UNIQUE,
             tags TEXT,
             connection_id TEXT,
             credential_pointer_address TEXT, -- Optional: points to a pointer holding encrypted credentials
             x REAL DEFAULT 0.0,
             y REAL DEFAULT 0.0,
             z INTEGER DEFAULT 0,
             created_at TEXT NOT NULL,
             last_modified TEXT NOT NULL)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS relationships
            (pointer_a_address TEXT NOT NULL,
             pointer_b_address TEXT NOT NULL,
             relationship TEXT,
             weight REAL,
             PRIMARY KEY (pointer_a_address, pointer_b_address),
             FOREIGN KEY(pointer_a_address) REFERENCES pointers(address) ON DELETE CASCADE,
             FOREIGN KEY(pointer_b_address) REFERENCES pointers(address) ON DELETE CASCADE)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS mailing_list
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             email TEXT NOT NULL UNIQUE,
             subscribed_at TEXT NOT NULL)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS access_keys
            (key TEXT PRIMARY KEY,
             domain_id TEXT NOT NULL,
             permissions TEXT NOT NULL DEFAULT '[]', -- e.g., '["admin_domain", "read_write"]'
             created_at TEXT NOT NULL,
             FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE)
        ''')
        self.db_manager.execute('''
            CREATE TABLE IF NOT EXISTS federations
            (id TEXT PRIMARY KEY,
             source_domain_id TEXT NOT NULL,
             target_domain_id TEXT NOT NULL,
             status TEXT NOT NULL, -- 'pending', 'accepted', 'rejected', 'revoked'
             permissions TEXT NOT NULL, -- JSON array of allowed actions, e.g., '["read_pointers"]'
             request_key TEXT NOT NULL UNIQUE,
             created_at TEXT NOT NULL,
             accepted_at TEXT,
             FOREIGN KEY(source_domain_id) REFERENCES domains(id) ON DELETE CASCADE,
             FOREIGN KEY(target_domain_id) REFERENCES domains(id) ON DELETE CASCADE)
        ''')
        self.db_manager.commit()

    def log(self, action: str, details: str = ""):
        # Use UTC for consistency
        timestamp = datetime.now(timezone.utc).isoformat()
        self.db_manager.execute(
            "INSERT INTO audit_log (timestamp, action, details) VALUES (?, ?, ?)", (timestamp, action, details))

    def commit(self):
        self.db_manager.commit()

# --- GyroidStructureModule Logic (Integrated) ---
# Helper function for gyroid calculation
def _hash_to_vector3(s: str) -> tuple[float, float, float]:
    """Hashes a string to a 3D vector (x, y, z) for gyroid placement."""
    # Use a consistent hash function
    hash_val = int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16)

    # Map hash to a 3D space (e.g., 0-100 for each dimension)
    x = (hash_val % 10000) / 100.0
    y = ((hash_val // 10000) % 10000) / 100.0
    z = ((hash_val // 100000000) % 10000) / 100.0
    return x, y, z
# The mathematical foundation is now part of the core, not a separate module.

def _calculate_gyroid_score(dx: float, dy: float, dz: float) -> float:
    """Calculates a gyroid score based on delta coordinates."""
    return abs(math.sin(dx) * math.cos(dy) + math.sin(dy) * math.cos(dz) + math.sin(dz) * math.cos(dx))

# --- CycleModule: Manager of the Fibonacci Renewal Cycle (Integrated) ---


class CycleModule:
    """
    """

    MAX_CYCLE_LIMIT=21
    RESET_STATE=1
    # Fibonacci-like sequence for optimal growth
    _OPTIMAL_SEQUENCE=[1, 2, 3, 5, 8, 13, 21]

    def start_cycle(self, operation_id: str):
        """Starts a new growth cycle for a given operation."""
        self._active_cycles[operation_id]=self.RESET_STATE

    def _get_next_optimal(self, current_index: int) -> int:
        """Finds the next step in the optimal Fibonacci-like sequence."""
        for num in self._OPTIMAL_SEQUENCE:
            if num > current_index:
                return num
        return self.MAX_CYCLE_LIMIT

        current_index=self._active_cycles[operation_id]
        next_index=self._get_next_optimal(
            current_index) if is_optimal else current_index + 1

        if next_index >= self.MAX_CYCLE_LIMIT:
            self._active_cycles[operation_id]=self.RESET_STATE
            return {"status": f"Cycle complete. Self-reflection complete. Gravitating back to {self.RESET_STATE}."}
        else:
            self._active_cycles[operation_id]=next_index
            return {"status": "Cycle advanced."}


# --- The Core of the Butterfly System ---
# This class will grow to encompass all the principles we've designed:
# zero-trust and a simplified pointer management paradigm.


# Constants for Genesis Pointer and Connection
GENESIS_DOMAIN_ID="dom_genesis_0000"
GENESIS_CONNECTION_ID="conn_genesis_0000"
GENESIS_POINTER_ADDRESS="ptr_genesis_0000"
# Separate DB for internal data
INTERNAL_DATA_DB_PATH="butterfly_internal_data.db"


class PointerHelper:
    """
    The PointerHelper acts as the central hub for managing the pointer graph. It
    handles all invocations for creating, modifying, and querying pointers, which
    act as Secure Resource Locators (SRLs).
    """

    def __init__(self, db_config: dict, gyroid_threshold: float=0.5):
        self.audit_module=AuditModule(db_config)
        self.encryption_module=EncryptionModule()
        self.cycle_module=CycleModule()
        self._gyroid_threshold=gyroid_threshold
        # --- Action Dispatcher ---
        # Refactors the large if/elif block into a modular, extensible dispatcher.
        # This aligns with the principle of "flexibility by design".
        self.actions={
            "create_pointer": self._handle_create_pointer,
            "get_pointer": self._handle_get_pointer,
            "add_neighbor": self._handle_add_neighbor,
            "get_neighbors": self._handle_get_neighbors,
            "initiate_federation": self._handle_initiate_federation,
            "accept_federation": self._handle_accept_federation,
            "revoke_federation": self._handle_revoke_federation,
            "get_federation_status": self._handle_get_federation_status,
            "create_domain": self._handle_create_domain,
            "generate_access_key": self._handle_generate_access_key,
            "get_domain_details": self._handle_get_domain_details,
            "revoke_access_key": self._handle_revoke_access_key,
            "set_connection_status": self._handle_set_connection_status,
            "create_connection": self._handle_create_connection,
            "assign_pointer_to_connection": self._handle_assign_pointer_to_connection,
            "invoke_through_connection": self._handle_invoke_through_connection,
            "get_pointers_for_connection": self._handle_get_pointers_for_connection,
            "search_pointers": self._handle_search_pointers,
            "search_by_proximity": self._handle_search_by_proximity,
            "get_graph_stats": self._handle_get_graph_stats,
            "get_admin_overview": self._handle_get_admin_overview,
            "get_graph_dot": self._handle_get_graph_dot,

            "create_circuit": self._handle_create_circuit,
            "get_pointer_summary": self._handle_get_pointer_summary,
            "execute_creation_model": self._handle_execute_creation_model,
            # Add other actions here...
        }
        print("[*] PointerHelper initialized.")

    def _evaluate_expression(self, expression: str, results: list):
        """Evaluates an expression against the results of previous steps."""
        try:
            # Split the expression into parts
            parts=expression.split('.')
            value=results
            for part in parts:
                # Remove brackets and quotes
                part=part.replace('[', '').replace(']', '').replace('\'', '')
                try:
                    # Try converting the part to an integer (for list indexing)
                    index=int(part)
                    value=value[index]
                except ValueError:
                    # Otherwise, treat it as a dictionary key
                    value=value.get(part)
                if value is None:
                    return None
            return value
        except (IndexError, KeyError, TypeError):
            return None

    def _substitute_values(self, action: dict, results: list) -> dict:
        """Substitutes placeholders in an action's parameters with evaluated values."""
        substituted_action={}
        for key, value in action.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                # This looks like a placeholder. Extract the expression.
                expression=value[value.find('{') + 1:value.find('}')]
                # Evaluate the expression
                evaluated_value=self._evaluate_expression(expression, results)
                if evaluated_value is not None:
                    # Substitute the value
                    substituted_action[key]=str(evaluated_value)
                else:
                    substituted_action[key]=value  # Leave it as is
            else:
                # Not a placeholder, just copy the value
                substituted_action[key]=value
        return substituted_action

    def _initialize_defaults(self):
        """Ensures default pointers exist if the database is empty."""
        # This is a placeholder for a more robust default creation/migration system.
        pass

    def _add_pointer_to_gyroid_structure(self, pointer_address: str):
        """
        Calculates and establishes gyroid-based relationships for a new pointer.
        Refactored to use a single, non-iterative SQL query, adhering to the
        "no iterations" paradigm for runtime operations.
        """
        # This query joins the pointers table with itself to calculate the gyroid score
        # for all pairs involving the new pointer, inserting relationships in one go.
        # The SQLite `abs`, `sin`, and `cos` functions are used for efficiency.
        self.db_manager.execute("""
            INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight)
            SELECT p1.address, p2.address, 'gyroid_related',
            abs(sin(p1.x - p2.x) * cos(p1.y - p2.y) + sin(p1.y - p2.y)
                * cos(p1.z - p2.z) + sin(p1.z - p2.z) * cos(p1.x - p2.x))
            FROM pointers p1, pointers p2
            WHERE p1.address = ? AND p1.address != p2.address
        """, (pointer_address,))
        self.audit_module.commit()

    def invoke(self, query: dict) -> dict:
        """This is the single entry point for all interactions with the system."""
        print(f"[*] Received invocation query: {query}")

        action_name=query.get("action")


        if not action_name:
            return {"status": "error", "message": "Query must include an 'action'."}

        handler=self.actions.get(action_name)
        if handler:
            return handler(query)

        else:
            return self._handle_unrefactored_action(query)

    def _execute_circuit(self, circuit_definition: list) -> list:
        """Executes a circuit definition, substituting placeholders with results from previous steps."""
        results=[]
        for action in circuit_definition:
            # Substitute values in the action
            substituted_action=self._substitute_values(action, results)

            # Execute the action
            action_name=substituted_action.get("action")
            if not action_name:
                return {"status": "error", "message": "Circuit action must include an 'action'."}

            handler=self.actions.get(action_name)
            if handler:
                result=handler(substituted_action)
                if result.get("status") == "success":
                    # Append the result to the list of results
                    results.append(result.get("result"))
                else:
                    # If any step fails, stop the circuit
                    return result
            else:
                return {"status": "error", "message": f"Unknown action: '{action_name}'"}
        return results

    def _handle_invoke_through_connection(self, query: dict) -> dict:
        if data_reference_str.startswith('internal_circuit::'):
            try:
                circuit_definition_str=data_reference_str.split('::', 1)[1]
                circuit_definition=json.loads(circuit_definition_str)
                # Recursively call invoke to execute the circuit
                return self._execute_circuit(circuit_definition)
            except Exception as e:
                return {"status": "error", "message": f"Failed to execute internal circuit: {str(e)}"}
            # Fallback for un-refactored or new actions
            return self._handle_unrefactored_action(query)

    def _get_predefined_api(self, api_type: str | None) -> dict | None:
        """
        Returns the data_reference and description for a predefined API connection.
        This method centralizes the definitions for out-of-the-box connections.
        If api_type is None, it returns all available APIs for the current edition.
        """
        # Community Edition APIs: Freely available, no keys required.
        community_apis={
            "news": {"data_reference": "https://www.reddit.com/.json", "description": "Free News Feed (Reddit)"},
            "trivia": {"data_reference": "https://opentdb.com/api.php?amount=1", "description": "Trivia Questions (Open Trivia DB)"},
            "knowledge": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Albert%20Einstein&format=json", "description": "General Knowledge (Wikipedia API)"},
            "history": {"data_reference": "http://numbersapi.com/random/date", "description": "Historical Date Facts (Numbers API)"},
            "joke_ai": {"data_reference": "https://v2.jokeapi.dev/joke/Any?format=json", "description": "Lightweight Joke Generation AI"},
            "advice_ai": {"data_reference": "https://api.adviceslip.com/advice", "description": "Lightweight Advice Generation AI"},
            "gis": {"data_reference": "https://nominatim.openstreetmap.org/search?q=Eiffel+Tower&format=json", "description": "Geographic Information (Nominatim)"},
            "city": {"data_reference": "https://api.teleport.org/api/cities/geonameid:5128581/", "description": "City Information (Teleport)"},
            "country": {"data_reference": "https://restcountries.com/v3.1/name/united", "description": "Country Information (REST Countries)"},
            "street": {"data_reference": "https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=40.714224&lon=-73.961452", "description": "Street Name (Nominatim)"},
            "landmarks": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=48.858|2.294&gsradius=10000&format=json", "description": "Earth Landmarks (Wikipedia GeoSearch)"},
            "animals": {"data_reference": "https://zoo-animal-api.herokuapp.com/animals/rand", "description": "Animal and Wildlife Database"},
            "cats": {"data_reference": "https://api.thecatapi.com/v1/breeds/abys", "description": "Cat Breed Information (TheCatAPI)"},
            "fish": {"data_reference": "https://www.fishwatch.gov/api/species", "description": "Fish Database (NOAA FishWatch)"},
            "plants": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Rose&format=json", "description": "Plant and Flower Database (Wikipedia)"},
            "games": {"data_reference": "https://www.freetogame.com/api/games", "description": "Free-to-Play Games Database (FreetoGame)"},
            "art": {"data_reference": "https://collectionapi.metmuseum.org/public/collection/v1/objects/436535", "description": "Public Domain Art (The Met Museum)"},
            "music_midi": {"data_reference": "https://musicbrainz.org/ws/2/artist/5b11f4ce-a62d-471e-81fc-a69a8278c7da?fmt=json", "description": "Music Information Database (MusicBrainz)"},
            "science_physics": {"data_reference": "https://api.le-systeme-solaire.net/rest/bodies/soleil", "description": "Physics and Astronomy API (The Solar System)"},
            "math": {"data_reference": "http://numbersapi.com/42/math", "description": "Math Facts (Numbers API)"},
            "music_theory": {"data_reference": "https://api.uberchord.com/v1/chords/C_maj", "description": "Music Education API (Uberchord)"},
            "food": {"data_reference": "https://world.openfoodfacts.org/api/v2/product/737628064502", "description": "Food Product Ingredients (Open Food Facts)"},
        }

        # Hosted Edition APIs: Includes community APIs plus private or key-required APIs.
        hosted_apis={
            **community_apis,
            "movies": {"data_reference": "https://api.themoviedb.org/3/search/movie?query=Inception&api_key=YOUR_API_KEY", "description": "Movie Database (TMDb) - Requires API Key"},
            "grammar": {"data_reference": "https://api.languagetool.org/v2/check?language=en-US&text=this+is+a+test", "description": "Writing and Grammar API (LanguageTool)"},
            "stock": {"data_reference": "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo", "description": "Stock Data (Alpha Vantage)"},
            "government": {"data_reference": "https://api.usa.gov/crime/fbi/sapi/api/data/nibrs/homicide/offense/agencies/count", "description": "Government API (FBI Crime Data)"}
        }

        # Default to "COMMUNITY" if the environment variable is not set.
        edition=os.environ.get('BUTTERFLY_EDITION', 'COMMUNITY').upper()
        api_definitions=hosted_apis if edition == 'HOSTED' else community_apis

        if api_type is None:
            return api_definitions  # Return all available APIs for the edition

        return api_definitions.get(api_type)

    def _handle_create_pointer(self, query: dict) -> dict:
            data_reference=query.get("data_reference")

            if not data_reference:
                return {"status": "error", "message": "Action 'create_pointer' requires a 'data_reference'."}

            cursor=self.db_manager.execute(
                "SELECT address FROM pointers WHERE data_reference = ?", (data_reference,))
            existing=cursor.fetchone()
            if existing:
                return {
                    "status": "error",
                    "message": f"A pointer for this data_reference already exists at address: {existing[0]}"
                }

            # Generate a unique, immutable address for the new pointer (SRL).
            address=f"ptr_{uuid.uuid4().hex[:12]}"

            # Create the pointer object. For now, it's a simple dictionary.
            new_pointer={
                "address": address,
                "description": query.get("description", ""),
                # What the pointer points to.
                "data_reference": data_reference,
                "tags": json.dumps(query.get("tags", [])),
                "x": query.get("x", 0.0),
                "y": query.get("y", 0.0),
                "z": 0,  # Z (delta) always starts at 0
                "connection_id": query.get("connection_id"),  # Can be null
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_modified": datetime.now(timezone.utc).isoformat()
            }
            # Update x, y, z coordinates based on hash if not provided
            if query.get("x") is None and query.get("y") is None and query.get("z") is None:
                new_pointer["x"], new_pointer["y"], new_pointer["z"]=_hash_to_vector3(
                    address)

            self.db_manager.execute("""
                INSERT INTO pointers(address, description, data_reference, tags, connection_id, x, y, z, created_at, last_modified)
                VALUES(: address, : description, : data_reference, : tags, : connection_id, : x, : y, : z, : created_at, : last_modified)
            """, new_pointer)
            self.audit_module.commit()

            print(
                f"[*] Pointer (SRL) created: {address} -> '{new_pointer['description']}'")

            # Calculate gyroid relationships for the new pointer
            self._add_pointer_to_gyroid_structure(address)

            # Prepare response, converting JSON strings back to lists
            new_pointer['tags'] = json.loads(new_pointer.get('tags', '[]')) # Ensure tags are a list for the response
            return {
                "status": "success",
                "result": {
                    "pointer": {
                        "address": new_pointer["address"],
                        "description": new_pointer["description"],
                        "data_reference": new_pointer["data_reference"],
                        "tags": new_pointer["tags"],
                        "connection_id": new_pointer["connection_id"],
                        "x": new_pointer["x"],
                        "y": new_pointer["y"],
                        "z": new_pointer["z"],
                        "created_at": new_pointer["created_at"],
                        "last_modified": new_pointer["last_modified"]
                    }
                }
            }

            # Fetch neighbors from the new relationships table
            cursor=self.db_manager.execute(
                "SELECT pointer_b_address, relationship, weight FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
            neighbors=[]  # Ensure neighbors is always a list
            for neighbor_row in cursor.fetchall():
                neighbors.append(
                    {"address": neighbor_row[0], "relationship": neighbor_row[1], "weight": neighbor_row[2]})
            pointer_data['neighbors']=neighbors

            return {"status": "success", "result": pointer_data}

    def _handle_add_neighbor(self, query: dict) -> dict:
            pointer_address=query.get("pointer_address")
            neighbor_address=query.get("neighbor_address")
            # Optional label for the edge
            relationship_label=query.get("relationship", "")
            weight=query.get("weight", 1.0)  # Optional weight for the edge

            if not pointer_address or not neighbor_address:
                return {"status": "error", "message": "Action 'add_neighbor' requires 'pointer_address' and 'neighbor_address'."}

            # Verify both pointers exist before creating a relationship.
            cursor=self.db_manager.execute("SELECT COUNT(*) FROM pointers WHERE address IN (?, ?)",
                           (pointer_address, neighbor_address))
            if cursor.fetchone()[0] != 2:
                return {"status": "error", "message": "One or both pointers (SRLs) not found. Cannot create relationship."}

            # Insert bidirectional relationships into the new table
            try:
                self.db_manager.execute("INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight) VALUES (?, ?, ?, ?)",
                               (pointer_address, neighbor_address, relationship_label, weight))
                self.db_manager.execute("INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight) VALUES (?, ?, ?, ?)",
                               (neighbor_address, pointer_address, relationship_label, weight))
            except sqlite3.IntegrityError:
                # This relationship already exists, which is fine.
                pass

            print(
                f"[*] Neighbor relationship created between {pointer_address} and {neighbor_address}.")

            # Update the last_modified timestamp for both pointers
            timestamp=datetime.now(timezone.utc).isoformat()
            self.db_manager.execute("UPDATE pointers SET last_modified = ? WHERE address = ?",
                           (timestamp, pointer_address))
            self.db_manager.execute("UPDATE pointers SET last_modified = ? WHERE address = ?",
                           (timestamp, neighbor_address))

            self.audit_module.commit()

            # Fetch the updated pointer to return
            response=self.invoke(
                {"action": "get_pointer", "pointer_address": pointer_address})

            return {
                "status": "success",
                "result": {"message": "Neighbor added successfully.", "pointer": response.get('result')}
            }

    def _handle_get_neighbors(self, query: dict) -> dict:
            pointer_address=query.get("pointer_address")

            if not pointer_address:
                return {"status": "error", "message": "Action 'get_neighbors' requires a 'pointer_address'."}

            cursor=self.db_manager.execute(
                "SELECT pointer_b_address, relationship, weight FROM relationships WHERE pointer_a_address = ?", (pointer_address,))

            neighbors=[]
            for row in cursor.fetchall():
                neighbors.append({
                    "address": row[0],
                    "relationship": row[1],
                    "weight": row[2]
                })

            return {"status": "success", "result": {"neighbors": neighbors}}

    def _handle_revoke_federation(self, query: dict) -> dict:
        """Revokes an existing federation, severing the trust link."""
        auth_context=query.get("auth_context", {})
        federation_id=query.get("federation_id")

        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can revoke a federation."}

        if not federation_id:
            return {"status": "error", "message": "Action 'revoke_federation' requires a 'federation_id'."}

        admin_domain_id=auth_context.get('domain_id')

        # Find the federation to verify ownership
        cursor=self.db_manager.execute(
            "SELECT source_domain_id, target_domain_id FROM federations WHERE id = ?", (
                federation_id,)
        )
        fed_row=cursor.fetchone()

        if not fed_row:
            return {"status": "error", "message": f"Federation with ID '{federation_id}' not found."}

        if admin_domain_id not in (fed_row['source_domain_id'], fed_row['target_domain_id']):
            return {"status": "error", "message": "Access denied. You are not an administrator of a domain involved in this federation."}

        # Update the status to 'revoked'
        cursor=self.db_manager.execute(
            "UPDATE federations SET status = 'revoked' WHERE id = ?", (federation_id,))
        self.audit_module.commit()

        self.audit_module.log(
            "revoke_federation", f"Federation '{federation_id}' was revoked by admin of domain '{admin_domain_id}'.")
        return {"status": "success", "result": {"message": "Federation has been revoked."}}

    def _handle_get_federation_status(self, query: dict) -> dict:
        """Gets the status of all federations involving the admin's domain."""
        auth_context=query.get("auth_context", {})
        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can view federation statuses."}

        domain_id=auth_context.get('domain_id')
        cursor=self.db_manager.execute(
            "SELECT * FROM federations WHERE source_domain_id = ? OR target_domain_id = ?", (domain_id, domain_id))
        federations=[dict(row) for row in cursor.fetchall()]

        return {"status": "success", "result": {"federations": federations}}

    def _handle_initiate_federation(self, query: dict) -> dict:
        """Initiates a federation request from a source domain to a target domain."""
        auth_context=query.get("auth_context", {})
        target_domain_id=query.get("target_domain_id")
        permissions=query.get(
            "permissions", ["read_pointers"])  # Default permission

        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can initiate federation."}

        if not target_domain_id:
            return {"status": "error", "message": "Action 'initiate_federation' requires a 'target_domain_id'."}

        source_domain_id=auth_context.get('domain_id')
        if source_domain_id == target_domain_id:
            return {"status": "error", "message": "A domain cannot federate with itself."}

        federation_id=f"fed_{uuid.uuid4().hex[:12]}"
        request_key=f"fed_req_{uuid.uuid4().hex}"

        fed_data={
            "id": federation_id,
            "source_domain_id": source_domain_id,
            "target_domain_id": target_domain_id,
            "status": "pending",
            "permissions": json.dumps(permissions),
            "request_key": request_key,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.db_manager.execute(
            "INSERT INTO federations (id, source_domain_id, target_domain_id, status, permissions, request_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fed_data['id'], fed_data['source_domain_id'], fed_data['target_domain_id'],
             fed_data['status'], fed_data['permissions'], fed_data['request_key'], fed_data['created_at'])
        )
        self.audit_module.commit()
        self.audit_module.log(
            "initiate_federation", f"Domain '{source_domain_id}' initiated federation with '{target_domain_id}'.")

        return {"status": "success", "result": {"message": "Federation request initiated. Securely share the request_key with the target domain administrator.", "request_key": request_key}}

    def _handle_accept_federation(self, query: dict) -> dict:
        """Accepts a pending federation request using a request_key."""
        auth_context=query.get("auth_context", {})
        request_key=query.get("request_key")

        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can accept a federation."}

        if not request_key:
            return {"status": "error", "message": "Action 'accept_federation' requires a 'request_key'."}

        target_domain_id=auth_context.get('domain_id')
        accepted_at=datetime.now(timezone.utc).isoformat()

        cursor=self.db_manager.execute(
            "UPDATE federations SET status = 'accepted', accepted_at = ? WHERE request_key = ? AND target_domain_id = ? AND status = 'pending'", (accepted_at, request_key, target_domain_id))
        self.audit_module.commit()

        if cursor.rowcount == 0:
            return {"status": "error", "message": "Invalid request key, or you are not the target domain, or the request is not pending."}

        self.audit_module.log(
            "accept_federation", f"Domain '{target_domain_id}' accepted federation request.")
        return {"status": "success", "result": {"message": "Federation successfully established."}}

    def _handle_create_domain(self, query: dict) -> dict:
            name=query.get("name")
            if not name:
                return {"status": "error", "message": "Action 'create_domain' requires a 'name'."}

            domain_id=f"dom_{uuid.uuid4().hex[:12]}"
            new_domain={
                "id": domain_id,
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            self.db_manager.execute(
                "INSERT INTO domains(id, name, created_at) VALUES(:id, :name, :created_at)", new_domain)

            self.audit_module.commit()
            self.audit_module.log(
                "create_domain", f"Domain '{name}' ({domain_id}) created.")

            return {
                "status": "success",
                "result": {"message": "Domain created successfully.", "domain": new_domain}
            }

    def _handle_get_domain_details(self, query: dict) -> dict:
        """Gets a full overview of a domain, its connections, and its keys."""
        auth_context=query.get("auth_context", {})
        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can view domain details."}

        domain_id=auth_context.get('domain_id')

        # Fetch domain info
        domain_cursor=self.db_manager.execute(
            "SELECT * FROM domains WHERE id = ?", (domain_id,))
        domain_info=dict(domain_cursor.fetchone())

        # Fetch connections
        connections_cursor=self.db_manager.execute(
            "SELECT id, name, description, status, allow_writes FROM connections WHERE domain_id = ?", (domain_id,))
        domain_info['connections']=[dict(row)
                                         for row in connections_cursor.fetchall()]

        # Fetch access keys (partial keys for security)
        keys_cursor=self.db_manager.execute(
            "SELECT key, permissions, created_at FROM access_keys WHERE domain_id = ?", (domain_id,))
        domain_info['access_keys']=[
            {
                "key_preview": f"key_...{row['key'][-4:]}",
                # For CLI/API use, but GUI should use preview
                "key": row['key'],
                "permissions": json.loads(row['permissions']),
                "created_at": row['created_at']
            } for row in keys_cursor.fetchall()
        ]

        return {"status": "success", "result": domain_info}

    def _handle_revoke_access_key(self, query: dict) -> dict:
        """Permanently revokes an access key."""
        auth_context=query.get("auth_context", {})
        key_to_revoke=query.get("key_to_revoke")

        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can revoke a key."}

        if not key_to_revoke:
            return {"status": "error", "message": "Action 'revoke_access_key' requires a 'key_to_revoke'."}

        admin_domain_id=auth_context.get('domain_id')

        # Check if the key to revoke belongs to the admin's domain
        key_cursor=self.db_manager.execute(
            "SELECT domain_id FROM access_keys WHERE key = ?", (key_to_revoke,))
        key_row=key_cursor.fetchone()

        if not key_row:
            return {"status": "error", "message": f"Access key not found."}
        if key_row['domain_id'] != admin_domain_id:
            return {"status": "error", "message": "Access denied. You can only revoke keys within your own domain."}
        if key_to_revoke == auth_context.get('key'):
            return {"status": "error", "message": "An admin key cannot revoke itself."}

        # Delete the key
        delete_cursor=self.db_manager.execute(
            "DELETE FROM access_keys WHERE key = ?", (key_to_revoke,))
        self.audit_module.commit()

        self.audit_module.log(
            "revoke_access_key", f"Access key ending in ...{key_to_revoke[-4:]} was revoked by admin of domain '{admin_domain_id}'.")
        return {"status": "success", "result": {"message": "Access key has been revoked."}}

    def _handle_set_connection_status(self, query: dict) -> dict:
        """Sets a connection's status to 'active' or 'disabled'."""
        auth_context=query.get("auth_context", {})
        connection_id=query.get("connection_id")
        status=query.get("status")

        if 'admin_domain' not in auth_context.get('permissions', []):
            return {"status": "error", "message": "Access denied. Only a domain admin can change a connection's status."}

        if not all([connection_id, status]):
            return {"status": "error", "message": "Action 'set_connection_status' requires 'connection_id' and 'status'."}

        if status not in ['active', 'disabled']:
            return {"status": "error", "message": "Status must be either 'active' or 'disabled'."}

        admin_domain_id=auth_context.get('domain_id')
        # Verify the connection is in the admin's domain
        conn_cursor=self.db_manager.execute(
            "SELECT domain_id FROM connections WHERE id = ?", (connection_id,))
        conn_row=conn_cursor.fetchone()

        if not conn_row or conn_row['domain_id'] != admin_domain_id:
            return {"status": "error", "message": "Access denied. Connection not found in your domain."}

        # Update the status
        self.db_manager.execute(
            "UPDATE connections SET status = ? WHERE id = ?", (status, connection_id))
        self.audit_module.commit()

        self.audit_module.log(
            "set_connection_status", f"Status for connection '{connection_id}' set to '{status}'.")
        return {"status": "success", "result": {"message": f"Connection '{connection_id}' status set to '{status}'."}}

    def _handle_generate_access_key(self, query: dict) -> dict:
            domain_id=query.get("domain_id")
            # This could be "admin_domain,read_write" or just "read_write"
            permissions_input=query.get("permissions", "read_write")

            if not domain_id:
                return {"status": "error", "message": "Action 'generate_access_key' requires a 'domain_id'."}

            # Parse permissions input into a JSON array string
            if isinstance(permissions_input, str):
                permissions_list=[
                    p.strip() for p in permissions_input.split(',') if p.strip()]
            elif isinstance(permissions_input, list):
                permissions_list=permissions_input
            else:
                return {"status": "error", "message": "Permissions must be a string (comma-separated) or a list."}

            # In a real system, you'd verify the user has rights to create a key for this domain.
            # For now, we assume the initial admin key is used.

            access_key=f"key_{uuid.uuid4().hex}"
            key_data={
                "key": access_key,
                "domain_id": domain_id,
                # Store as JSON string
                "permissions": json.dumps(permissions_list),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.db_manager.execute(
                "INSERT INTO access_keys (key, domain_id, permissions, created_at) VALUES (?, ?, ?, ?)",
                (access_key, domain_id,
                 key_data['permissions'], key_data['created_at'])
            )
            self.audit_module.commit()
            self.audit_module.log(
                "generate_access_key", f"Generated '{permissions_input}' key for domain '{domain_id}'.")
            return {
                "status": "success",
                "result": {"message": "Access key generated. Store this securely.", "access_key": access_key, "details": key_data}
            }

    def _handle_create_connection(self, query: dict) -> dict:
            name=query.get("name")
            api_type=query.get("api_type")  # NEW: Optional API type
            domain_id=query.get("domain_id")
            if not name or not domain_id:
                return {"status": "error", "message": "Action 'create_connection' requires a 'name' and 'domain_id'."}

            # If an API type is specified, get the data_reference and description from the predefined list.
            api_data=self._get_predefined_api(api_type) if api_type else None
            data_reference=api_data["data_reference"] if api_data else query.get(
                "data_reference")
            description=api_data["description"] if api_data else query.get(
                "description", "")

            connection_id=f"conn_{uuid.uuid4().hex[:12]}"
            new_connection={
                "id": connection_id, "name": name, "description": description, "status": "active",
                "allow_writes": 1 if query.get("allow_writes") is True else 0, "domain_id": domain_id, # Added missing created_at
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            self.db_manager.execute("""
                INSERT INTO connections(id, name, description, allow_writes, created_at, domain_id)
                VALUES(: id, : name, : description, : allow_writes, : created_at, : domain_id)
            """, new_connection)
            self.audit_module.commit()

            return {
                "status": "success",
                "result": {"message": "Connection created successfully.", "connection": new_connection}
            }

    def _handle_assign_pointer_to_connection(self, query: dict) -> dict:
            pointer_address=query.get("pointer_address")
            connection_id=query.get("connection_id")
            auth_context=query.get("auth_context", {})  # From JWT

            if not all([pointer_address, connection_id, auth_context]):
                return {"status": "error", "message": "Action 'assign_pointer_to_connection' requires 'pointer_address', 'connection_id', and an access key."}

            # Verify the key has rights to the domain of the connection
            cursor=self.db_manager.execute(
                "SELECT domain_id FROM connections WHERE id = ?", (connection_id,))
            # Also check if the connection is active
            cursor=self.db_manager.execute(
                "SELECT domain_id, status FROM connections WHERE id = ?", (
                    connection_id,)
            )
            conn_row=cursor.fetchone()
            if conn_row and conn_row['status'] == 'disabled':
                return {"status": "error", "message": f"Access denied. Connection '{connection_id}' is disabled."}
            conn_domain_row=cursor.fetchone()  # The domain this connection belongs to
            # The domain of the app making the request
            requesting_domain_id=auth_context.get('domain_id')

            # Allow if the key's domain is the same as the connection's domain OR if there is an accepted federation.
            is_owner=conn_domain_row and conn_domain_row[0] == requesting_domain_id
            is_federated=conn_domain_row and self._is_federated(
                requesting_domain_id, conn_domain_row[0])
            if not (is_owner or is_federated):
                return {"status": "error", "message": "Access denied. The provided key is not valid for the domain containing this connection."}

            cursor=self.db_manager.execute("UPDATE pointers SET connection_id = ? WHERE address = ?",
                                             (connection_id, pointer_address))
            self.audit_module.commit()

            if cursor.rowcount == 0:
                return {"status": "error", "message": f"Pointer (SRL) not found: {pointer_address}"}

            return {"status": "success", "result": {"message": f"Pointer {pointer_address} assigned to connection {connection_id}."}}

    def _handle_invoke_through_connection(self, query: dict) -> dict:
            connection_id=query.get("connection_id")
            pointer_address=query.get("pointer_address")
            auth_context=query.get("auth_context", {})  # From JWT

            if not all([connection_id, pointer_address, auth_context]):
                return {"status": "error", "message": "Action 'invoke_through_connection' requires 'connection_id', 'pointer_address', and an access key."}

            # Verify the key has rights to the domain of the connection
            cursor=self.db_manager.execute(
                "SELECT domain_id FROM connections WHERE id = ?", (connection_id,))
            conn_domain_row=cursor.fetchone()  # The domain this connection belongs to
            # The domain of the app making the request
            requesting_domain_id=auth_context.get('domain_id')

            # Allow if the key's domain is the same as the connection's domain OR if there is an accepted federation.
            is_owner=conn_domain_row and conn_domain_row[0] == requesting_domain_id
            is_federated=conn_domain_row and self._is_federated(
                requesting_domain_id, conn_domain_row[0])
            if not (is_owner or is_federated):
                return {"status": "error", "message": "Access denied. The provided key is not valid for the domain containing this connection."}

            cursor=self.db_manager.execute(
                "SELECT connection_id, data_reference FROM pointers WHERE address = ?", (pointer_address,))
            row=cursor.fetchone()

            if not row:
                return {"status": "error", "message": f"Pointer (SRL) not found: {pointer_address}"}

            # This is a more complex proxy model now.
            # The SRL is the internal concept, but the invocation now performs the final data fetch.
            # This aligns with the "knock on the door" + "credentials" model.
            # The original SRL generation logic is superseded by this more secure proxy.

            # 1. Fetch pointer details, including the credential link
            p_conn_id, data_reference_str=row

            if p_conn_id != connection_id:
                return {
                    "status": "error",
                    "message": f"Access denied. Pointer (SRL) {pointer_address} does not belong to connection {connection_id}."
                }

            # Handle internal circuit pointers
            if data_reference_str.startswith('internal_circuit::'):
                try:
                    circuit_definition_str = data_reference_str.split('::', 1)[1]
                    circuit_definition = json.loads(circuit_definition_str)
                    # Execute the circuit directly
                    return {"status": "success", "result": self._execute_circuit(circuit_definition)}
                except Exception as e:
                    return {"status": "error", "message": f"Failed to execute internal circuit: {str(e)}"}

            # 2. Check if this invocation requires native credentials
            cursor=self.db_manager.execute(
                "SELECT credential_pointer_address FROM pointers WHERE address = ?", (pointer_address,))
            cred_ptr_row=cursor.fetchone()
            native_auth_header=None

            if cred_ptr_row and cred_ptr_row['credential_pointer_address']:
                cred_ptr_address=cred_ptr_row['credential_pointer_address']
                # Fetch the credential pointer
                cred_cursor=self.db_manager.execute(
                    "SELECT data_reference FROM pointers WHERE address = ?", (cred_ptr_address,))
                cred_data_row=cred_cursor.fetchone()
                if not cred_data_row:
                    return {"status": "error", "message": f"Credential pointer '{cred_ptr_address}' not found."}

                # 3. Decrypt credentials in memory
                try:
                    credentials=self.encryption_module.decrypt(
                        cred_data_row['data_reference'])
                    # Assuming credentials are in the format {"header": "Authorization", "token": "Bearer ..."}
                    if "header" in credentials and "token" in credentials:
                        native_auth_header={
                            credentials["header"]: credentials["token"]}
                    else:
                         return {"status": "error", "message": "Malformed credential pointer data."}
                except Exception as e:
                    return {"status": "error", "message": f"Failed to decrypt credentials: {str(e)}"}

            # 4. Make the final, authenticated request to the target datastore
            try:
                headers=native_auth_header if native_auth_header else {}
                response=requests.get(data_reference_str,
                                      headers=headers, timeout=10)
                response.raise_for_status()
                data_payload=response.json()

                self.audit_module.log(
                    action="invoke_and_proxy",
                    details=f"Successfully proxied request for {pointer_address} for key ending in ...{auth_context.get('key', 'unknown')[-4:]}"
                )

                return {
                    "status": "success",
                    "result": {"message": "Invocation successful. Data retrieved.", "data": data_payload}
                }
            except Exception as e:
                interpretation=f"Failed to access the final resource for pointer '{pointer_address}'."
                details=f"The system could not retrieve data from the target datastore at '{data_reference_str}'. The error was: {str(e)}"
                return {
                    "status": "interpretation_rendered",
                    "result": {"interpretation": interpretation, "details": details}
                }

    def _handle_create_circuit(self, query: dict) -> dict:
        """Creates a new pointer that encapsulates a sequence of actions (a circuit)."""
        circuit_definition=query.get("circuit_definition")
        description=query.get("description")

        if not circuit_definition or not isinstance(circuit_definition, list):
            return {"status": "error", "message": "Action 'create_circuit' requires a 'circuit_definition' as a list of actions."}
        if not description:
            return {"status": "error", "message": "Action 'create_circuit' requires a 'description'."}

        # The data_reference for a circuit pointer is a special internal command.
        # We serialize the circuit definition into the reference itself.
        data_reference=f"internal_circuit::{json.dumps(circuit_definition)}"

        # Use the existing _handle_create_pointer logic to create the pointer
        create_query={
            "action": "create_pointer",
            "data_reference": data_reference,
            "description": description,
            "tags": query.get("tags", ["circuit"])
        }

        response=self._handle_create_pointer(create_query)
        self.audit_module.log(
            "create_circuit", f"Created circuit pointer for '{description}'.")
        return response

    def _handle_get_pointers_for_connection(self, query: dict) -> dict:
            connection_id=query.get("connection_id")
            auth_context=query.get("auth_context", {})  # From JWT
            if not connection_id or not auth_context:
                return {"status": "error", "message": "Action 'get_pointers_for_connection' requires 'connection_id' and an access key."}

            # Verify the key has rights to the domain of the connection
            cursor=self.db_manager.execute(
                "SELECT domain_id FROM connections WHERE id = ?", (connection_id,))
            conn_domain_row=cursor.fetchone()  # The domain this connection belongs to
            # The domain of the app making the request
            requesting_domain_id=auth_context.get('domain_id')

            # Allow if the key's domain is the same as the connection's domain OR if there is an accepted federation.
            is_owner=conn_domain_row and conn_domain_row[0] == requesting_domain_id
            is_federated=conn_domain_row and self._is_federated(
                requesting_domain_id, conn_domain_row[0])
            if not (is_owner or is_federated):
                return {"status": "error", "message": "Access denied. The provided key is not valid for the domain containing this connection."}

            cursor=self.db_manager.execute(
                "SELECT * FROM pointers WHERE connection_id = ?", (connection_id,))
            rows=cursor.fetchall()

            pointers_list=[]
            for row in rows:
                pointer_data={
                    "address": row[0], "description": row[1], "data_reference": row[2],
                    "tags": json.loads(row[3]), "connection_id": row[4],
                    "x": row[5], "y": row[6], "z": row[7],
                    "created_at": row[8], "last_modified": row[9]
                }
                pointers_list.append(pointer_data)

            return {
                "status": "success",
                "result": {
                    "pointers": pointers_list
                }
            }

    def _handle_search_pointers(self, query: dict) -> dict:
            search_term=query.get("search_term")  # For description
            # For a list of tags to include
            search_tags=query.get("search_tags")
            exclude_tags=query.get("exclude_tags")
            tag_match_mode=query.get("tag_match_mode", "ALL").upper()

            if not search_term and not search_tags:
                return {"status": "error", "message": "Action 'search_pointers' requires at least a 'search_term' or 'search_tags'."}

            where_clauses=[]
            params=[]

            if search_term:
                where_clauses.append("description LIKE ?")
                params.append(f"%{search_term}%")

            if search_tags:
                if not isinstance(search_tags, list):
                    return {"status": "error", "message": "'search_tags' must be a list."}
                if tag_match_mode == "ALL":
                    for tag in search_tags:
                        where_clauses.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')
                elif tag_match_mode == "ANY":
                    any_clause=" OR ".join(
                        ["tags LIKE ?" for _ in search_tags])
                    where_clauses.append(f"({any_clause})")
                    params.extend([f'%"{tag}"%' for tag in search_tags])
                else:
                    return {"status": "error", "message": "'tag_match_mode' must be 'ANY' or 'ALL'."}

            if exclude_tags:
                if not isinstance(exclude_tags, list):
                    return {"status": "error", "message": "'exclude_tags' must be a list."}
                for tag in exclude_tags:
                    where_clauses.append("tags NOT LIKE ?")
                    params.append(f'%"{tag}"%')

            # Build the final query
            # Use json_group_array and json_each to perform the search efficiently in the DB
            sql_query="""
                SELECT p.address, p.description, p.data_reference, p.tags, p.connection_id, p.x, p.y, p.z, p.created_at, p.last_modified
                FROM pointers p
            """
            if where_clauses:
                sql_query += " WHERE " + " AND ".join(where_clauses)

            cursor=self.db_manager.execute(sql_query, params)
            rows=cursor.fetchall()

            # No iteration needed here. The data is already fetched.
            matching_pointers=[{
                "address": row[0], "description": row[1], "data_reference": row[2],
                "tags": json.loads(row[3]), "connection_id": row[4],
                "x": row[5], "y": row[6], "z": row[7],
                "created_at": row[8], "last_modified": row[9]
            } for row in rows]

            # --- Cycle Module Integration ---
            # A search returning many results is considered less "optimal"
            # because it has a higher processing cost.
            is_search_optimal=len(matching_pointers) < 50
            # We would need to pass an operation ID to this action to track it.
            # self.cycle_module.advance_cycle(op_id, is_optimal=is_search_optimal)

            print(
                f"[*] Search found {len(matching_pointers)} matching pointers.")

            return {
                "status": "success",
                "result": {
                    "count": len(matching_pointers),
                    "pointers": matching_pointers,
                }
            }

    def _handle_search_by_proximity(self, query: dict) -> dict:
            origin_pointer_address=query.get("origin_pointer_address")
            radius=query.get("radius")

            if not origin_pointer_address or radius is None:
                return {"status": "error", "message": "Action 'search_by_proximity' requires 'origin_pointer_address' and 'radius'."}

            # 1. Get the coordinates of the origin pointer. This is a single, fast lookup.
            cursor=self.db_manager.execute(
                "SELECT x, y, z FROM pointers WHERE address = ?", (origin_pointer_address,))
            origin_row=cursor.fetchone()
            if not origin_row:
                return {"status": "error", "message": f"Origin pointer (SRL) not found: {origin_pointer_address}"}
            ox, oy, oz=origin_row

            # 2. Perform a native mathematical search.
            # This query calculates the squared Euclidean distance directly in the database,
            # which is highly efficient. It avoids iterating through pointers in the application.
            # We use squared distance to avoid the expensive SQRT() function in the DB.
            radius_squared=float(radius) ** 2
            # This single query fetches all necessary data, removing the need for a loop.
            cursor=self.db_manager.execute("""
                SELECT address, description, data_reference, tags, connection_id, x, y, z, created_at, last_modified
                FROM pointers
                WHERE((x - ?) * (x - ?)) + ((y - ?) * (y - ?)) + ((z - ?) * (z - ?)) <= ?
                AND address != ?
            """, (ox, ox, oy, oy, oz, oz, radius_squared, origin_pointer_address))

            rows=cursor.fetchall()
            matching_pointers=[{
                "address": row[0], "description": row[1], "data_reference": row[2],
                "tags": json.loads(row[3]), "connection_id": row[4],
                "x": row[5], "y": row[6], "z": row[7],
                "created_at": row[8], "last_modified": row[9]
            } for row in rows]

            return {"status": "success", "result": {"count": len(matching_pointers), "pointers": matching_pointers}}

    def _handle_get_graph_stats(self, query: dict) -> dict:
            cursor=self.db_manager.execute("SELECT COUNT(*) FROM pointers")
            num_pointers=cursor.fetchone()[0]

            # Count relationships by dividing the total rows in the relationships table by 2 (for bidirectional links)
            cursor=self.db_manager.execute(
                "SELECT COUNT(*) FROM relationships")
            num_relationships=cursor.fetchone()[0] // 2

            stats={
                "total_pointers": num_pointers,
                "total_relationships": num_relationships
            }

            return {
                "status": "success",
                "result": stats
            }

    def _handle_get_admin_overview(self, query: dict) -> dict:
            auth_context=query.get("auth_context", {})  # From JWT
            if 'admin_domain' not in auth_context.get('permissions', []):
                return {"status": "error", "message": "Access denied. This action requires admin permissions."}

            domain_id=auth_context.get('domain_id')
            cursor=self.db_manager.execute(
                "SELECT id, name, created_at FROM domains WHERE id = ?", (domain_id,))
            domain_row=cursor.fetchone()
            domains=[{"id": domain_row[0], "name": domain_row[1],
                "created_at": domain_row[2], "connections": []}] if domain_row else []

            domain_ids=[d['id'] for d in domains]
            if not domain_ids:
                return {"status": "success", "result": {"domains": []}}

            # This part is complex to do without a loop in pure SQL without window functions or CTEs which might be complex.
            # For now, this loop is acceptable as it's an admin function, not a core, high-frequency operation.
            # A future optimization could be a more complex single query if performance becomes an issue.
            # The logic remains the same.

            return {"status": "success", "result": {"domains": domains}}

    def _handle_get_graph_dot(self, query: dict) -> dict:
            # Start building the DOT language string. 'graph' for undirected edges.
            dot_string='graph G {\n    node [shape=box, style="rounded,filled", fillcolor=lightyellow];\n'

            # Keep track of edges to avoid duplicates in an undirected graph.
            drawn_edges=set()

            all_pointers_res=self.db_manager.execute(
                "SELECT address, description FROM pointers").fetchall()
            all_relationships_res=self.db_manager.execute(
                "SELECT pointer_a_address, pointer_b_address, relationship, weight FROM relationships").fetchall()

            for row in all_pointers_res:
                address, description=row

                # Add a node for each pointer.
                description=description.replace(
                    '"', '\\"') if description else address
                dot_string += f'    "{address}" [label="{description}"];\n'

            for row in all_relationships_res:
                address, neighbor_address, relationship, weight=row
                # Add edges for each neighbor relationship.

                # To avoid duplicates, create a sorted tuple of the pair.
                edge=tuple(sorted((address, neighbor_address)))
                if edge not in drawn_edges:
                    attributes=[]
                    if relationship:
                        attributes.append(
                            f'label="{relationship}"')
                    if weight:
                        attributes.append(f'weight="{weight}"')

                    dot_string += f'    "{address}" -- "{neighbor_address}" [{", ".join(attributes)}];\n'
                    drawn_edges.add(edge)

            dot_string += "}"

            return {
                "status": "success",
                "result": {"dot_string": dot_string}
            }

    def _handle_get_pointer_summary(self, query: dict) -> dict:
            pointer_address=query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'get_pointer_summary' requires a 'pointer_address'."}

            cursor=self.db_manager.execute(
                "SELECT description, tags, created_at, last_modified, connection_id, x, y, z FROM pointers WHERE address = ?", (pointer_address,))
            row=cursor.fetchone()

            if not row:
                return {"status": "error", "message": f"Pointer (SRL) not found: {pointer_address}"}

            description, tags_json, created_at, last_modified, connection_id, x, y, z=row
            tags=json.loads(tags_json)

            # Get neighbor count from the new table
            cursor=self.db_manager.execute(
                "SELECT COUNT(*) FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
            neighbor_count=cursor.fetchone()[0]

            summary={
                "address": pointer_address,
                "description": description,
                "connection_id": connection_id,
                "tags": tags,
                "neighbor_count": neighbor_count,
                "created_at": created_at,
                "last_modified": last_modified
            }

            return {
                "status": "success",
                "result": summary
            }

    def _handle_execute_creation_model(self, query: dict) -> dict:
            pointer_address=query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'execute_creation_model' requires a 'pointer_address'."}

            op_id=f"op_{uuid.uuid4().hex[:8]}"
            # --- Step 1: "Let there be Light" - The Invocation ---
            # The process begins with a single query, the initial spark.
            self.cycle_module.start_cycle(op_id)
            self.audit_module.log(
                "creation_model_step1", f"Invocation received for {pointer_address}. Operation ID: {op_id}")

            # --- Step 2: "Let there be an Idea" - The Determination Graph ---
            # The "idea" is the pointer itself and its immediate context (neighbors).
            # This is the first "vertical" step, adding/multiplying context.
            graph_response=self.invoke(
                {"action": "get_pointer", "pointer_address": pointer_address})
            determination_graph={
                "root": graph_response.get("result"),
                "neighbors": graph_response.get("result", {}).get("neighbors", [])
            }
            root_pointer=determination_graph["root"]
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step2", f"Determined local graph for {pointer_address}.")

            # --- Step 3: "Let there be Connection" - The Logic Gate ---
            # We apply logical rules, like a "horizontal" step (dividing/subtracting) to filter or test the idea.
            data_ref=root_pointer.get(
                "data_reference", "") if root_pointer else ""
            is_secure_url=data_ref.startswith("https://")
            has_connection=root_pointer.get(
                "connection_id") is not None if root_pointer else False
            has_public_tag="public" in root_pointer.get(
                "tags", []) if root_pointer else False
            logic_gate_result={
                "is_secure_url": is_secure_url,
                "is_public_and_connected": has_connection and has_public_tag
            }
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step3", f"Logic gate check for {pointer_address}: {logic_gate_result}")

            # --- Step 4: The Decision Tree ---
            # The sum of the previous steps allows for a higher-level decision.
            risk_level="low"
            if not logic_gate_result["is_public_and_connected"]:
                risk_level="high"  # Fails security gate
            elif root_pointer and root_pointer.get("z", 0) > 5:
                risk_level="medium"  # High number of deltas/versions
            decision_tree_result={"risk_level": risk_level}
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step4", f"Decision tree result for {pointer_address}: {decision_tree_result}")

            # --- Step 5: The Fibonacci Spiral - Proximity Analysis ---
            # We expand context by finding conceptually close pointers in the 3D space,
            # representing the compounding growth of the Fibonacci spiral.
            proximity_results=[]
            # Ensure coordinates exist
            if root_pointer and root_pointer.get('x') is not None:
                ox, oy, oz=root_pointer.get('x', 0), root_pointer.get(
                    'y', 0), root_pointer.get('z', 0)
                radius_squared=5.0 ** 2                
                cursor=self.db_manager.execute("""
                    SELECT address, description FROM pointers
                    WHERE((x - ?) * (x - ?)) + ((y - ?) * (y - ?)) + ((z - ?) * (z - ?)) <= ?
                    AND address != ?
                """, (ox, ox, oy, oy, oz, oz, radius_squared, pointer_address))
                for row in cursor.fetchall():
                    proximity_results.append(
                        {"address": row[0], "description": row[1]})
                self.cycle_module.advance_cycle(op_id)
                self.audit_module.log(
                    "creation_model_step5", f"Proximity analysis found {len(proximity_results)} nearby pointers for {pointer_address}.")

            # --- Step 6: The Presentation ---
            # All analysis is assembled into a single, coherent object.
            presentation_data={
                "determination_graph": determination_graph,
                "logical_analysis": {
                    "logic_gate": logic_gate_result,
                    "decision_tree": decision_tree_result,
                    "proximity_analysis": {
                        "nearby_pointers": proximity_results
                    }
                },
                "summary": f"Analysis for pointer {pointer_address} complete. Risk level assessed as '{risk_level}'."
            }
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step6", f"Presentation prepared for {pointer_address}.")

            # --- Step 7: Self-Reflection and Reset ---
            # The cycle completes, knowledge is logged, and gravitates back to 1.
            cycle_end_status=self.cycle_module.advance_cycle(op_id)
            final_render={
                "status": "creation_model_complete",
                "result": presentation_data,
                "_cycle_status": cycle_end_status
            }
            self.audit_module.log(
                "creation_model_step7", f"Self-reflection complete for {pointer_address}. {cycle_end_status.get('status')}")

            # As part of the final step, we can create a shortcut to this entire process.
            # Create a data_reference that encapsulates the entire circuit call.
            circuit_data_reference=f"internal_circuit::{json.dumps({'action': 'execute_creation_model', 'pointer_address': pointer_address})}"
            cursor=self.db_manager.execute(
                "SELECT address FROM pointers WHERE data_reference = ?", (circuit_data_reference,))
            existing_shortcut=cursor.fetchone()

            if existing_shortcut:
                shortcut_address=existing_shortcut[0]
                final_render["result"]["shortcut_pointer_address"]=shortcut_address
                self.audit_module.log(
                    "circuit_pointer_exists", f"Shortcut pointer {shortcut_address} already exists for this circuit.")
            else:
                shortcut_description=f"Circuit for '{pointer_address}'"
                # Use the internal `create_pointer` logic to create the shortcut
                shortcut_query={
                    "action": "create_pointer",
                    "data_reference": circuit_data_reference,
                    "description": shortcut_description
                }
                create_response=self.invoke(shortcut_query)
                final_render["result"]["shortcut_pointer_address"]=create_response.get(
                    "result", {}).get("pointer", {}).get("address")

            return final_render

    def _handle_unrefactored_action(self, query: dict) -> dict:
        if query.get("action") == "clear_audit_log":
            auth_context=query.get("auth_context", {})  # From JWT

            # This action is now scoped to the domain of the admin key.
            # A super-admin might have different logic.
            if auth_context.get('permissions') != 'admin':
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}

            key_str=f"key ending in ...{auth_context.get('key', 'unknown')[-4:]}"

            try:
                self.db_manager.execute("DELETE FROM audit_log")
                self.audit_module.commit()
                # Log the clear action itself as the first new entry
                self.audit_module.log(
                    "clear_audit_log", f"Audit log cleared by admin key '{key_str}'.")
                return {"status": "success", "result": {"message": "Audit log has been cleared."}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while clearing the audit log: {str(e)}"}

        elif query.get("action") == "get_all_tags":
            try:
                cursor=self.db_manager.execute("SELECT tags FROM pointers")
                rows=cursor.fetchall()

                all_tags=set()
                for row in rows:
                    if row[0]:  # Ensure the tags column is not null
                        try:
                            tags_list=json.loads(row[0])
                            if isinstance(tags_list, list):
                                all_tags.update(tags_list)
                        except (json.JSONDecodeError, TypeError):
                            # Ignore malformed JSON in the tags column for this row
                            continue

                sorted_tags=sorted(list(all_tags))
                self.audit_module.log(
                    "get_all_tags", f"Retrieved {len(sorted_tags)} unique tags.")
                return {"status": "success", "result": {"tags": sorted_tags}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching tags: {str(e)}"}

        elif query.get("action") == "get_unassigned_pointers":
            # This is an administrative action. Check for admin privileges.
            auth_context=query.get("auth_context", {})
            if 'admin_domain' not in auth_context.get('permissions', []):
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}
            try:
                # Find all pointers where connection_id is NULL
                cursor=self.db_manager.execute(
                    "SELECT address, description, created_at FROM pointers WHERE connection_id IS NULL")
                rows=cursor.fetchall()

                unassigned_pointers=[
                    {"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]

                self.audit_module.log(
                    "get_unassigned_pointers", f"Found {len(unassigned_pointers)} unassigned pointers.")
                return {"status": "success", "result": {"pointers": unassigned_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching unassigned pointers: {str(e)}"}

        elif query.get("action") == "get_available_apis":
            try:
                edition=os.environ.get(
                    'BUTTERFLY_EDITION', 'COMMUNITY').upper()
                # The _get_predefined_api method is designed to get a single API.
                # We can introspect it to build the full list.
                # This is a simplified way to get the source dictionaries.
                # This will be the full dict for the edition
                all_apis=self._get_predefined_api(None)

                # Format for client consumption
                available_apis=[{"api_type": key, "description": value["description"]}
                    for key, value in all_apis.items()]

                return {"status": "success", "result": {"edition": edition, "available_apis": available_apis}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching available APIs: {str(e)}"}

        elif query.get("action") == "find_pointers_by_tag":
            tag=query.get("tag")
            if not tag:
                return {"status": "error", "message": "Action 'find_pointers_by_tag' requires a 'tag'."}

            try:
                # Use LIKE to find the tag within the JSON array string
                # The quotes ensure we match the whole tag string, e.g., "user_data"
                cursor=self.db_manager.execute(
                    "SELECT address, description, created_at FROM pointers WHERE tags LIKE ?", (f'%"{tag}"%',))
                rows=cursor.fetchall()

                matching_pointers=[
                    {"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]

                self.audit_module.log(
                    "find_pointers_by_tag", f"Found {len(matching_pointers)} pointers with tag '{tag}'.")
                return {"status": "success", "result": {"pointers": matching_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while finding pointers by tag: {str(e)}"}

        elif query.get("action") == "get_pointer_relationships":
            pointer_address=query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'get_pointer_relationships' requires a 'pointer_address'."}

            try:
                # Use DISTINCT to get a unique list of relationship types for the pointer
                cursor=self.db_manager.execute(
                    "SELECT DISTINCT relationship FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
                rows=cursor.fetchall()

                # Extract the relationship strings from the query result
                relationship_types=[row[0] for row in rows if row[0]]

                self.audit_module.log(
                    "get_pointer_relationships", f"Found {len(relationship_types)} unique relationship types for pointer '{pointer_address}'.")
                return {"status": "success", "result": {"relationships": sorted(relationship_types)}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching pointer relationships: {str(e)}"}

        elif query.get("action") == "get_isolated_pointers":
            # This is an administrative action. Check for admin privileges.
            auth_context=query.get("auth_context", {})  # From JWT
            # We check for the specific 'admin_domain' permission.
            if 'admin_domain' not in auth_context.get('permissions', []):
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}

            try:
                # Use a LEFT JOIN to find pointers that have no entries in the relationships table.
                cursor=self.db_manager.execute("""
                    SELECT p.address, p.description, p.created_at
                    FROM pointers p
                    LEFT JOIN relationships r ON p.address=r.pointer_a_address
                    WHERE r.pointer_a_address IS NULL
                """)
                rows=cursor.fetchall()
                isolated_pointers=[
                    {"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]
                self.audit_module.log(
                    "get_isolated_pointers", f"Found {len(isolated_pointers)} isolated pointers.")
                return {"status": "success", "result": {"pointers": isolated_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching isolated pointers: {str(e)}"}

        elif query.get("action") == "get_relationships_by_type":
            relationship_type=query.get("relationship_type")
            if not relationship_type:
                return {"status": "error", "message": "Action 'get_relationships_by_type' requires a 'relationship_type'."}

            try:
                # Query for relationships of a specific type.
                # The pointer_a_address < pointer_b_address condition prevents duplicates from the bidirectional links.
                rows=self.db_manager.execute(
                    "SELECT pointer_a_address, pointer_b_address, weight FROM relationships WHERE relationship = ? AND pointer_a_address < pointer_b_address", (relationship_type,))
                rows=cursor.fetchall()

                relationships=[
                    {"pointer_a": row[0], "pointer_b": row[1], "weight": row[2]} for row in rows]

                self.audit_module.log(
                    "get_relationships_by_type", f"Found {len(relationships)} relationships of type '{relationship_type}'.")
                return {"status": "success", "result": {"relationships": relationships}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching relationships by type: {str(e)}"}

        else:
            return {"status": "error", "message": f"Unknown action: '{query.get('action')}'"}


# --- Flask Web Server Setup ---
# This provides the API endpoint for applications to interact with the PointerHelper.
app=Flask(__name__)
CONFIG_FILE='config/config.json'
# Enables Cross-Origin Resource Sharing (CORS) to allow web apps to call this API.
CORS(app)

# Instantiate our one and only PointerHelper for the Community Edition.
butterfly_helper=None  # Will be initialized after config is loaded

# --- Caching for Report Endpoint ---
_report_cache={}
# Cache reports for 5 minutes. A real implementation detail.
CACHE_TTL_SECONDS=300

# --- JWT Authentication Setup ---

# It's critical to load this from an environment variable in production.
app.config['SECRET_KEY']=os.environ.get(
    'JWT_SECRET_KEY', 'default-super-secret-key-for-dev')


def token_required(f):
    @ wraps(f)
    def decorated(*args, **kwargs):
        token=None
        if 'Authorization' in request.headers:
            # Passthrough mode for external authentication (e.g., reverse proxy)
            auth_mode=_config.get('authentication_mode', 'internal')
            if auth_mode == 'passthrough':
                return f({'key': 'passthrough_user', 'domain_id': 'passthrough_domain', 'permissions': 'admin'}, *args, **kwargs)

            # Expected format: "Bearer <token>"
            auth_header=request.headers['Authorization']
            try:
                token=auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Bearer token malformed. Expected format: Bearer <token>'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decode the token using the app's secret key
            payload=jwt.decode(
                token, app.config['SECRET_KEY'], algorithms=["HS256"])
            access_key=payload.get('access_key')
            if not access_key:
                return jsonify({'message': 'Token is invalid! Missing access_key.'}), 401

            # Verify the access key and get its context (domain, permissions)
            cursor=butterfly_helper.audit_module.db_manager.execute(
                "SELECT domain_id, permissions FROM access_keys WHERE key = ?", (access_key,))
            key_row=cursor.fetchone()
            if not key_row:
                return jsonify({'message': 'Access key is invalid or has been revoked.'}), 401

            domain_id, permissions_json = key_row
            permissions_list = json.loads(
                permissions_json) # Parse JSON string to list
            payload['auth_context']={
                'key': access_key, 'domain_id': domain_id, 'permissions': permissions_list}
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(payload, *args, **kwargs)
    return decorated


@ app.route('/invoke', methods=['POST'])
@ token_required
# token_payload is now passed from the decorator
def handle_invocation(token_payload):
    encrypted_query_str=request.data.decode('utf-8')
    try:
        query=butterfly_helper.encryption_module.decrypt(encrypted_query_str)
        # Inject the auth context from the token into the query for permission checks
        query['auth_context']=token_payload.get('auth_context')
        response=butterfly_helper.invoke(query)
        encrypted_response=butterfly_helper.encryption_module.encrypt(
            response)
        return encrypted_response, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return butterfly_helper.encryption_module.encrypt({"status": "error", "message": f"Failed to process encrypted request: {str(e)}"}), 400, {'Content-Type': 'text/plain'}


@ app.route('/capabilities', methods=['GET'])
def get_capabilities():
   
    # This endpoint can now use the same logic as the API action
    api_definitions=butterfly_helper._get_predefined_api(
        None)  # Gets the full dictionary
    if api_definitions:
        return jsonify(api_definitions)
    return jsonify({})


@ app.route('/report', methods=['GET'])
def generate_report():

    api_type=request.args.get('type')
    if not api_type:
        return jsonify({"error": "API type parameter is missing"}), 400

    # Check cache first
    current_time=time.time()
    if api_type in _report_cache and (current_time - _report_cache[api_type]['timestamp']) < CACHE_TTL_SECONDS:
        print(f"[*] Serving report for '{api_type}' from cache.")
        return jsonify(_report_cache[api_type]['data'])

    print(
        f"[*] Generating new report for '{api_type}'. Cache miss or expired.")
    api_info=butterfly_helper._get_predefined_api(api_type)
    if not api_info:
        return jsonify({"error": "Invalid API type"}), 404

    try:
        response=requests.get(api_info['data_reference'], timeout=10)
        response.raise_for_status()
        data_payload=response.json()
        report_data={"source": api_info['description'], "data": data_payload}


        # Store the new report in the cache
        _report_cache[api_type]={
            'timestamp': current_time, 'data': report_data}
        return jsonify(report_data)
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return jsonify({"error": f"Failed to fetch or parse data from API: {str(e)}"})


@ app.route('/')
def index():
    # Serve the main landing page.
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'landing.html')


@ app.route('/subscribe', methods=['POST'])
def subscribe():

    email=request.form.get('email')
    if not email:
        return "Email address is required.", 400

    try:
        timestamp=datetime.now(timezone.utc).isoformat()
        butterfly_helper.audit_module.db_manager.execute("INSERT INTO mailing_list (email, subscribed_at) VALUES (?, ?)",
                       (email, timestamp))
        butterfly_helper.audit_module.commit()
        return "<h3>Subscription Successful!</h3><p>Thank you for subscribing. You've been added to the mailing list for updates and patches.</p><a href='/'>Return Home</a>", 200
    except sqlite3.IntegrityError:
        # This error occurs if the email is not unique.
        return "<h3>Already Subscribed</h3><p>This email address is already on our mailing list.</p><a href='/'>Return Home</a>", 200
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


def run_setup_wizard():
    print("--- Butterfly System Setup Wizard ---")
    print("This will create a 'config.json' file to store your settings.")

    # 1. Configure Database
    db_choice=input(
        "Use default SQLite database (butterfly_local.db)? [Y/n]: ").lower().strip()
    if db_choice == 'n':
        db_path=input(
            "Enter the full path for your SQLite database file: ").strip()
    else:
        db_path="butterfly_local.db"

    # 2. Configure Authentication
    print("\nSelect Authentication Mode:")
    print("1. Internal (Default): The server will manage JWTs for secure access.")
    print("2. Passthrough: The server will bypass JWT validation. Use this only if you are running this service behind a reverse proxy that handles authentication.")
    auth_choice=input("Enter your choice [1]: ").strip()
    if auth_choice == '2':
        auth_mode='passthrough'
        print(
            "\n[!] WARNING: Passthrough mode is insecure if the server is exposed directly to the internet.")
    else:
        auth_mode='internal'

    # 3. No more admin_app_id, it's handled by access keys.

    config_data={
        "database_path": db_path,
        "authentication_mode": auth_mode
    }

    # Ensure the config directory exists
    if not os.path.exists(os.path.dirname(CONFIG_FILE)):
        os.makedirs(os.path.dirname(CONFIG_FILE))

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

    print(
        f"\nConfiguration saved to '{CONFIG_FILE}'. You can delete this file to run the wizard again.")
    return config_data


def load_config():

    if not os.path.exists(CONFIG_FILE):
        return run_setup_wizard()
    else:
        with open(CONFIG_FILE, 'r') as f:
            print(f"[*] Loading configuration from '{CONFIG_FILE}'.")
            return json.load(f)


def main():

    # Load config or run wizard before initializing the helper
    global _config, butterfly_helper
    _config = load_config()
    db_config = {
        "path": _config.get("database_path", "butterfly_local.db")
    }
    butterfly_helper = PointerHelper(db_config=db_config)

    print("Starting Butterfly server...")
    # In a production Docker environment, gunicorn would be used. This is for local dev.
    # debug=False for production-like behavior.
    app.run(host='0.0.0.0', port=5001, debug=False)


  