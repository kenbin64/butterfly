from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
import json
import time
from datetime import datetime, timezone
import os
import sqlite3
import base64
import requests
from cryptography.fernet import Fernet
import shutil
import jwt
from functools import wraps
import argparse
import math
import csv
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
        self.fernet = Fernet(key)

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
    def __init__(self, db_path="butterfly_local.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             timestamp TEXT NOT NULL,
             action TEXT NOT NULL,
             details TEXT)
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS domains
            (id TEXT PRIMARY KEY,
             name TEXT NOT NULL,
             owner_app_id TEXT NOT NULL,
             created_at TEXT NOT NULL)
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS connections
            (id TEXT PRIMARY KEY,
             name TEXT NOT NULL,
             description TEXT,
             allow_writes INTEGER DEFAULT 0,
             created_at TEXT NOT NULL,
             domain_id TEXT NOT NULL,
             FOREIGN KEY(domain_id) REFERENCES domains(id))
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS pointers
            (address TEXT PRIMARY KEY,
             description TEXT,
             data_reference TEXT NOT NULL UNIQUE,
             tags TEXT,
             connection_id TEXT,
             x REAL DEFAULT 0.0,
             y REAL DEFAULT 0.0,
             z INTEGER DEFAULT 0,
             created_at TEXT NOT NULL,
             last_modified TEXT NOT NULL)
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS relationships
            (pointer_a_address TEXT NOT NULL,
             pointer_b_address TEXT NOT NULL,
             relationship TEXT,
             weight REAL,
             PRIMARY KEY (pointer_a_address, pointer_b_address),
             FOREIGN KEY(pointer_a_address) REFERENCES pointers(address) ON DELETE CASCADE,
             FOREIGN KEY(pointer_b_address) REFERENCES pointers(address) ON DELETE CASCADE)
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS mailing_list
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             email TEXT NOT NULL UNIQUE,
             subscribed_at TEXT NOT NULL)
        ''')
        print(f"[*] AuditModule initialized. Logging to '{db_path}'.")

    def log(self, action: str, details: str = ""):
        # Use UTC for consistency
        timestamp = datetime.now(timezone.utc).isoformat()
        self.conn.execute("INSERT INTO audit_log (timestamp, action, details) VALUES (?, ?, ?)",
                          (timestamp, action, details))
        self.conn.commit()

    def get_cursor(self):
        """Provides a cursor for database operations."""
        return self.conn.cursor()

    def commit(self):
        """Commits the current transaction."""
        self.conn.commit()

# --- GyroidStructureModule Logic (Integrated) ---
# The mathematical foundation is now part of the core, not a separate module.

import hashlib

def _hash_to_vector3(pointer_address: str) -> tuple[float, float, float]:
    """
    Statically hashes a pointer address to a conceptual 3D coordinate.
    This is a design-time choice for mapping pointers to our mathematical space.
    It's deterministic and non-iterative.
    """
    h = hashlib.sha256(pointer_address.encode()).hexdigest()
    # Normalize hash segments to a range of [0, 2*pi] for trigonometric functions
    x = (int(h[0:8], 16) / (2**32 - 1)) * (2 * math.pi)
    y = (int(h[8:16], 16) / (2**32 - 1)) * (2 * math.pi)
    z = (int(h[16:24], 16) / (2**32 - 1)) * (2 * math.pi)
    return (x, y, z)


def _gyroid_equation(c1: tuple[float, ...], c2: tuple[float, ...]) -> float:
    """
    Calculates the gyroid relationship score between two coordinates.
    This is a direct, non-iterative mathematical calculation ("butterfly principle").
    """
    dx, dy, dz = c1[0] - c2[0], c1[1] - c2[1], c1[2] - c2[2]
    # Simplified Schwarz Diamond equation. A result closer to 0 means a stronger link.
    return abs(math.sin(dx) * math.cos(dy) + math.sin(dy) * math.cos(dz) + math.sin(dz) * math.cos(dx))

# --- CycleModule: Manager of the Fibonacci Renewal Cycle (Integrated) ---


class CycleModule:
    """
    Manages the growth and complexity cycle of operations within the system.
    It tracks an operation's complexity on a scale from 1 to 21.
    When a cycle completes (reaches 21), it resets to 1.
    """

    MAX_CYCLE_LIMIT = 21
    RESET_STATE = 1
    # Fibonacci-like sequence for optimal growth
    _OPTIMAL_SEQUENCE = [1, 2, 3, 5, 8, 13, 21]

    def __init__(self):
        self._active_cycles: dict[str, int] = {}

    def start_cycle(self, operation_id: str):
        """Starts a new growth cycle for a given operation."""
        self._active_cycles[operation_id] = self.RESET_STATE

    def _get_next_optimal(self, current_index: int) -> int:
        """Finds the next step in the optimal Fibonacci-like sequence."""
        for num in self._OPTIMAL_SEQUENCE:
            if num > current_index:
                return num
        return self.MAX_CYCLE_LIMIT

    def advance_cycle(self, operation_id: str, is_optimal: bool = True) -> dict:
        """Advances the cycle for an operation."""
        if operation_id not in self._active_cycles:
            return {"error": f"No active cycle for operation '{operation_id}'."}

        current_index = self._active_cycles[operation_id]
        next_index = self._get_next_optimal(
            current_index) if is_optimal else current_index + 1

        if next_index >= self.MAX_CYCLE_LIMIT:
            self._active_cycles[operation_id] = self.RESET_STATE
            return {"status": f"Cycle complete. Self-reflection complete. Gravitating back to {self.RESET_STATE}."}
        else:
            self._active_cycles[operation_id] = next_index
            return {"status": "Cycle advanced."}


# --- The Core of the Butterfly System ---
# This class will grow to encompass all the principles we've designed:
# zero-trust and a simplified pointer management paradigm.


class PointerHelper:
    """
    The PointerHelper acts as the central hub for managing the pointer graph.
    It handles all invocations for creating, modifying, and querying pointers.
    """

    def __init__(self, gyroid_threshold: float = 0.5):
        db_path = _config.get('database_path', 'butterfly_local.db')
        self.audit_module = AuditModule(db_path=db_path)
        self.encryption_module = EncryptionModule()
        self.cycle_module = CycleModule()
        self._initialize_defaults()
        self._gyroid_threshold = gyroid_threshold
        # --- Action Dispatcher ---
        # Refactors the large if/elif block into a modular, extensible dispatcher.
        # This aligns with the principle of "flexibility by design".
        self.actions = {
            "create_pointer": self._handle_create_pointer,
            "get_pointer": self._handle_get_pointer,
            "add_neighbor": self._handle_add_neighbor,
            "get_neighbors": self._handle_get_neighbors,
            "create_domain": self._handle_create_domain,
            "create_connection": self._handle_create_connection,
            "assign_pointer_to_connection": self._handle_assign_pointer_to_connection,
            "invoke_through_connection": self._handle_invoke_through_connection,
            "get_pointers_for_connection": self._handle_get_pointers_for_connection,
            "search_pointers": self._handle_search_pointers,
            "search_by_proximity": self._handle_search_by_proximity,
            "get_graph_stats": self._handle_get_graph_stats,
            "get_admin_overview": self._handle_get_admin_overview,
            "get_graph_dot": self._handle_get_graph_dot,
            "get_pointer_summary": self._handle_get_pointer_summary,
            "execute_creation_model": self._handle_execute_creation_model,
            # Add other actions here...
        }
        print("[*] PointerHelper initialized.")

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
        cursor = self.audit_module.get_cursor()
        # This query joins the pointers table with itself to calculate the gyroid score
        # for all pairs involving the new pointer, inserting relationships in one go.
        # The SQLite `abs`, `sin`, and `cos` functions are used for efficiency.
        cursor.execute("""
            INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight)
            SELECT p1.address, p2.address, 'gyroid_related', 
                   ABS(SIN(p1.x - p2.x) * COS(p1.y - p2.y) + SIN(p1.y - p2.y) * COS(p1.z - p2.z) + SIN(p1.z - p2.z) * COS(p1.x - p2.x))
            FROM pointers p1, pointers p2
            WHERE p1.address = ? 
              AND p2.address != p1.address
              AND ABS(SIN(p1.x - p2.x) * COS(p1.y - p2.y) + SIN(p1.y - p2.y) * COS(p1.z - p2.z) + SIN(p1.z - p2.z) * COS(p1.x - p2.x)) < ?
        """, (pointer_address, self._gyroid_threshold))
        
        self.audit_module.commit()

    def _get_predefined_api(self, api_type: str) -> dict:
        """Returns a dictionary containing the data_reference and description for a predefined API type."""
        # Community Edition APIs: Publicly accessible without keys.
        community_apis = {
            # General Info & Knowledge
            "weather": {"data_reference": "https://wttr.in/?format=j1", "description": "Weather forecast (wttr.in)"},
            "news": {"data_reference": "https://www.reddit.com/.json", "description": "Free News Feed (Reddit)"},
            "trivia": {"data_reference": "https://opentdb.com/api.php?amount=1", "description": "Trivia Questions (Open Trivia DB)"},
            "knowledge": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Albert%20Einstein&format=json", "description": "General Knowledge (Wikipedia API)"}, # Example query
            "history": {"data_reference": "http://numbersapi.com/random/date", "description": "Historical Date Facts (Numbers API)"},
            "joke_ai": {"data_reference": "https://v2.jokeapi.dev/joke/Any?format=json", "description": "Lightweight Joke Generation AI"},
            "advice_ai": {"data_reference": "https://api.adviceslip.com/advice", "description": "Lightweight Advice Generation AI"},
            # Geography & Landmarks
            "gis": {"data_reference": "https://nominatim.openstreetmap.org/search?q=Eiffel+Tower&format=json", "description": "Geographic Information (Nominatim)"}, # Example query
            "city": {"data_reference": "https://api.teleport.org/api/cities/geonameid:5128581/", "description": "City Information (Teleport)"},
            "country": {"data_reference": "https://restcountries.com/v3.1/name/united", "description": "Country Information (REST Countries)"},
            "street": {"data_reference": "https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=40.714224&lon=-73.961452", "description": "Street Name (Nominatim)"},
            "landmarks": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=48.858|2.294&gsradius=10000&format=json", "description": "Earth Landmarks (Wikipedia GeoSearch)"},
            # Biology & Nature
            "animals": {"data_reference": "https://zoo-animal-api.herokuapp.com/animals/rand", "description": "Animal and Wildlife Database"},
            "cats": {"data_reference": "https://api.thecatapi.com/v1/breeds/abys", "description": "Cat Breed Information (TheCatAPI)"},
            "fish": {"data_reference": "https://www.fishwatch.gov/api/species", "description": "Fish Database (NOAA FishWatch)"},
            "plants": {"data_reference": "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Rose&format=json", "description": "Plant and Flower Database (Wikipedia)"}, # Example query
            # Media & Entertainment
            "games": {"data_reference": "https://www.freetogame.com/api/games", "description": "Free-to-Play Games Database (FreetoGame)"},
            "art": {"data_reference": "https://collectionapi.metmuseum.org/public/collection/v1/objects/436535", "description": "Public Domain Art (The Met Museum)"},
            "music_midi": {"data_reference": "https://musicbrainz.org/ws/2/artist/5b11f4ce-a62d-471e-81fc-a69a8278c7da?fmt=json", "description": "Music Information Database (MusicBrainz)"},
            # STEM & Education
            "science_physics": {"data_reference": "https://api.le-systeme-solaire.net/rest/bodies/soleil", "description": "Physics and Astronomy API (The Solar System)"},
            "math": {"data_reference": "http://numbersapi.com/42/math", "description": "Math Facts (Numbers API)"},
            "music_theory": {"data_reference": "https://api.uberchord.com/v1/chords/C_maj", "description": "Music Education API (Uberchord)"},
            "food": {"data_reference": "https://world.openfoodfacts.org/api/v2/product/737628064502", "description": "Food Product Ingredients (Open Food Facts)"}, # Example query
        }

        # Hosted Edition APIs: Includes community APIs plus private or key-required APIs.
        hosted_apis = {
            **community_apis,
            # Media & Entertainment
            "movies": {"data_reference": "https://api.themoviedb.org/3/search/movie?query=Inception&api_key=YOUR_API_KEY", "description": "Movie Database (TMDb) - Requires API Key"},
            # STEM & Education
            "grammar": {"data_reference": "https://api.languagetool.org/v2/check?language=en-US&text=this+is+a+test", "description": "Writing and Grammar API (LanguageTool)"}, # Example query
            # Business & Products
            "stock": {"data_reference": "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo", "description": "Stock Data (Alpha Vantage)"},
            # Government & Sports
            "government": {"data_reference": "https://api.usa.gov/crime/fbi/sapi/api/data/nibrs/homicide/offense/agencies/count", "description": "Government API (FBI Crime Data)"}
        }

        # Default to "COMMUNITY" if the environment variable is not set.
        edition = os.environ.get('BUTTERFLY_EDITION', 'COMMUNITY').upper()

        api_definitions = hosted_apis if edition == 'HOSTED' else community_apis

        return api_definitions.get(api_type)

    def invoke(self, query: dict) -> dict:
        """This is the single entry point for all interactions with the system."""
        print(f"[*] Received invocation query: {query}")

        action_name = query.get("action")

        if not action_name:
            return {"status": "error", "message": "Query must include an 'action'."}

        handler = self.actions.get(action_name)
        if handler:
            return handler(query)
        else:
            # Fallback for un-refactored or new actions
            return self._handle_unrefactored_action(query)

    def _handle_create_pointer(self, query: dict) -> dict:
            data_reference = query.get("data_reference")

            if not data_reference:
                return {"status": "error", "message": "Action 'create_pointer' requires a 'data_reference'."}

            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT address FROM pointers WHERE data_reference = ?", (data_reference,))
            existing = cursor.fetchone()
            if existing:
                return {
                    "status": "error",
                    "message": f"A pointer for this data_reference already exists at address: {existing[0]}"
                }

            # Generate a unique, immutable address for the new pointer.
            address = f"ptr_{uuid.uuid4().hex[:12]}"

            # Create the pointer object. For now, it's a simple dictionary.
            new_pointer = {
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
                new_pointer["x"], new_pointer["y"], new_pointer["z"] = _hash_to_vector3(
                    address)

            cursor.execute("""
                INSERT INTO pointers (address, description, data_reference, tags, connection_id, x, y, z, created_at, last_modified)
                VALUES (:address, :description, :data_reference, :tags, :connection_id, :x, :y, :z, :created_at, :last_modified)
            """, new_pointer)
            self.audit_module.commit()

            print(
                f"[*] Pointer created: {address} -> '{new_pointer['description']}'")

            # Calculate gyroid relationships for the new pointer
            self._add_pointer_to_gyroid_structure(address)

            # Prepare response, converting JSON strings back to lists
            new_pointer['tags'] = json.loads(new_pointer.get('tags', '[]'))
            return {
                "status": "success",
                "result": {"message": "Pointer created successfully.", "pointer": new_pointer}
            }

    def _handle_get_pointer(self, query: dict) -> dict:
            pointer_address = query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'get_pointer' requires a 'pointer_address'."}

            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT * FROM pointers WHERE address = ?", (pointer_address,))
            row = cursor.fetchone()

            if row is None:
                return {"status": "error", "message": f"Pointer not found: {pointer_address}"}

            # Convert row to a dictionary
            pointer_data = {
                "address": row[0],
                "description": row[1],
                "data_reference": row[2],
                "tags": json.loads(row[3]),
                "connection_id": row[4],
                "x": row[5],
                "y": row[6],
                "z": row[7],
                "created_at": row[8],
                "last_modified": row[9]
            }

            # Fetch neighbors from the new relationships table
            cursor.execute(
                "SELECT pointer_b_address, relationship, weight FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
            neighbors = []  # Ensure neighbors is always a list
            for neighbor_row in cursor.fetchall():
                neighbors.append(
                    {"address": neighbor_row[0], "relationship": neighbor_row[1], "weight": neighbor_row[2]})
            pointer_data['neighbors'] = neighbors

            return {"status": "success", "result": pointer_data}

    def _handle_add_neighbor(self, query: dict) -> dict:
            pointer_address = query.get("pointer_address")
            neighbor_address = query.get("neighbor_address")
            # Optional label for the edge
            relationship_label = query.get("relationship", "")
            weight = query.get("weight", 1.0)  # Optional weight for the edge

            if not pointer_address or not neighbor_address:
                return {"status": "error", "message": "Action 'add_neighbor' requires 'pointer_address' and 'neighbor_address'."}

            cursor = self.audit_module.get_cursor()

            # Verify both pointers exist before creating a relationship.
            cursor.execute("SELECT COUNT(*) FROM pointers WHERE address IN (?, ?)",
                           (pointer_address, neighbor_address))
            if cursor.fetchone()[0] != 2:
                return {"status": "error", "message": "One or both pointers not found. Cannot create relationship."}

            # Insert bidirectional relationships into the new table
            try:
                cursor.execute("INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight) VALUES (?, ?, ?, ?)",
                               (pointer_address, neighbor_address, relationship_label, weight))
                cursor.execute("INSERT INTO relationships (pointer_a_address, pointer_b_address, relationship, weight) VALUES (?, ?, ?, ?)",
                               (neighbor_address, pointer_address, relationship_label, weight))
            except sqlite3.IntegrityError:
                # This relationship already exists, which is fine.
                pass

            print(
                f"[*] Neighbor relationship created between {pointer_address} and {neighbor_address}.")

            # Update the last_modified timestamp for both pointers
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE pointers SET last_modified = ? WHERE address = ?",
                           (timestamp, pointer_address))
            cursor.execute("UPDATE pointers SET last_modified = ? WHERE address = ?",
                           (timestamp, neighbor_address))

            self.audit_module.commit()

            # Fetch the updated pointer to return
            response = self.invoke(
                {"action": "get_pointer", "pointer_address": pointer_address})

            return {
                "status": "success",
                "result": {"message": "Neighbor added successfully.", "pointer": response.get('result')}
            }

    def _handle_get_neighbors(self, query: dict) -> dict:
            pointer_address = query.get("pointer_address")

            if not pointer_address:
                return {"status": "error", "message": "Action 'get_neighbors' requires a 'pointer_address'."}

            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT pointer_b_address, relationship, weight FROM relationships WHERE pointer_a_address = ?", (pointer_address,))

            neighbors = []
            for row in cursor.fetchall():
                neighbors.append({
                    "address": row[0],
                    "relationship": row[1],
                    "weight": row[2]
                })

            return {"status": "success", "result": {"neighbors": neighbors}}

    def _handle_create_domain(self, query: dict) -> dict:
            # This should come from the JWT payload in a real scenario
            owner_app_id = query.get("owner_app_id")
            name = query.get("name")
            if not name or not owner_app_id:
                return {"status": "error", "message": "Action 'create_domain' requires a 'name' and 'owner_app_id'."}

            domain_id = f"dom_{uuid.uuid4().hex[:12]}"
            new_domain = {
                "id": domain_id,
                "name": name,
                "owner_app_id": owner_app_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            cursor = self.audit_module.get_cursor()
            cursor.execute("""
                INSERT INTO domains (id, name, owner_app_id, created_at)
                VALUES (:id, :name, :owner_app_id, :created_at)
            """, new_domain)
            self.audit_module.commit()

            return {
                "status": "success",
                "result": {"message": "Domain created successfully.", "domain": new_domain}
            }

    def _handle_create_connection(self, query: dict) -> dict:
            name = query.get("name")
            api_type = query.get("api_type")  # NEW: Optional API type
            domain_id = query.get("domain_id")
            if not name or not domain_id:
                return {"status": "error", "message": "Action 'create_connection' requires a 'name' and 'domain_id'."}

            # If an API type is specified, get the data_reference and description from the predefined list.
            api_data = self._get_predefined_api(api_type) if api_type else None
            data_reference = api_data["data_reference"] if api_data else query.get(
                "data_reference")
            description = api_data["description"] if api_data else query.get(
                "description", "")

            connection_id = f"conn_{uuid.uuid4().hex[:12]}"
            new_connection = {
                "id": connection_id, "name": name, "description": description,
                "data_reference": data_reference,  # NEW: Store the data_reference
                "allow_writes": 1 if query.get("allow_writes") is True else 0,
                "created_at": datetime.now(timezone.utc).isoformat(), "domain_id": domain_id
            }

            cursor = self.audit_module.get_cursor()
            cursor.execute("""
                INSERT INTO connections (id, name, description, allow_writes, created_at, domain_id)
                VALUES (:id, :name, :description, :allow_writes, :created_at, :domain_id)
            """, new_connection)
            self.audit_module.commit()

            return {
                "status": "success",
                "result": {"message": "Connection created successfully.", "connection": new_connection}
            }

    def _handle_assign_pointer_to_connection(self, query: dict) -> dict:
            pointer_address = query.get("pointer_address")
            connection_id = query.get("connection_id")
            requesting_app_id = query.get("app_id")  # From JWT

            if not all([pointer_address, connection_id, requesting_app_id]):
                return {"status": "error", "message": "Action 'assign_pointer_to_connection' requires 'pointer_address', 'connection_id', and 'app_id'."}

            cursor = self.audit_module.get_cursor()

            # Verify ownership of the connection
            cursor.execute(
                "SELECT d.owner_app_id FROM connections c JOIN domains d ON c.domain_id = d.id WHERE c.id = ?", (connection_id,))
            owner_row = cursor.fetchone()
            if not owner_row or owner_row[0] != requesting_app_id:
                return {"status": "error", "message": f"Access denied. Application '{requesting_app_id}' does not have permission for connection '{connection_id}'."}

            cursor.execute("UPDATE pointers SET connection_id = ? WHERE address = ?",
                           (connection_id, pointer_address))
            self.audit_module.commit()

            if cursor.rowcount == 0:
                return {"status": "error", "message": f"Pointer not found: {pointer_address}"}

            return {"status": "success", "result": {"message": f"Pointer {pointer_address} assigned to connection {connection_id}."}}

    def _handle_invoke_through_connection(self, query: dict) -> dict:
            connection_id = query.get("connection_id")
            pointer_address = query.get("pointer_address")
            requesting_app_id = query.get("app_id")  # From JWT

            if not all([connection_id, pointer_address, requesting_app_id]):
                return {"status": "error", "message": "Action 'invoke_through_connection' requires 'connection_id', 'pointer_address', and 'app_id'."}

            cursor = self.audit_module.get_cursor()

            # Verify ownership of the connection
            cursor.execute(
                "SELECT d.owner_app_id FROM connections c JOIN domains d ON c.domain_id = d.id WHERE c.id = ?", (connection_id,))
            owner_row = cursor.fetchone()
            if not owner_row or owner_row[0] != requesting_app_id:
                return {"status": "error", "message": f"Access denied. Application '{requesting_app_id}' does not have permission for connection '{connection_id}'."}

            cursor.execute(
                "SELECT connection_id, data_reference FROM pointers WHERE address = ?", (pointer_address,))
            row = cursor.fetchone()

            if not row:
                return {"status": "error", "message": f"Pointer not found: {pointer_address}"}

            p_conn_id, data_reference = row

            if p_conn_id != connection_id:
                return {
                    "status": "error",
                    "message": f"Access denied. Pointer {pointer_address} does not belong to connection {connection_id}."
                }

            # The "seeing" mechanism: The connection is now allowed to see the data.
            # In a real scenario, this is where you would fetch the data from the `data_reference`.
            # To enforce that connections "speak JSON", we will now attempt to parse the data_reference.
            # This simulates fetching data and ensuring it's valid JSON.
            try:
                # --- Real-world data fetching ---
                if data_reference.startswith('internal_circuit::'):
                    circuit_command_str = data_reference.split('::', 1)[1]
                    circuit_query = json.loads(circuit_command_str)
                    self.audit_module.log(
                        "invoke_circuit", f"Connection {connection_id} is invoking an internal circuit: {circuit_query}")
                    # Recursively call invoke to execute the circuit
                    return self.invoke(circuit_query)
                elif data_reference.startswith(('http://', 'https://')):
                    response = requests.get(data_reference, timeout=5)
                    response.raise_for_status()  # Raise an exception for bad status codes
                    content_type = response.headers.get(
                        'Content-Type', '').lower()

                    if 'application/json' in content_type:
                        # It's JSON, return it as a structured object
                        data_payload = response.json(),
                        render_hint = 'json'
                    else:
                        # It's a native format (HTML, image, etc.). Base64-encode it.
                        data_payload = {
                            "content": base64.b64encode(response.content).decode('utf-8'),
                            "content_type": content_type,
                            "encoding": "base64"
                        },
                        # Provide a hint based on the content type
                        render_hint = 'image' if 'image' in content_type else 'html'

                else:
                    # For other schemes like file:// or if the reference is the data itself
                    if data_reference.startswith('file://'):
                        render_hint = 'json'  # Default to json for decrypted internal data
                    
                    path = data_reference.split('file://', 1)[1]


                    # Security Check: Ensure the path is within the user's home directory.
                    # This is a critical security measure to prevent access to system files.
                    home_dir = os.path.expanduser("~")
                    safe_path = os.path.abspath(path)
                    if not safe_path.startswith(home_dir):
                        return {"status": "error", "message": "Access denied. Path is outside the allowed user directory."}

                    if not os.path.exists(safe_path) or not os.path.isdir(safe_path):
                        return {"status": "error", "message": f"Directory not found at path: {safe_path}"}

                    # List directory contents
                    contents = os.listdir(safe_path)
                    data_payload = {
                        "path": safe_path,
                        "files": [f for f in contents if os.path.isfile(os.path.join(safe_path, f))],
                        "directories": [d for d in contents if os.path.isdir(os.path.join(safe_path, d))]
                    }
                    render_hint = 'file_system'
                    
                    else:
                        # This path assumes the reference itself is the data, likely encrypted JSON.
                        data_payload = self.encryption_module.decrypt(data_reference)
                        render_hint = 'json'

            except Exception as e:
                # If data is unavailable, return an interpretation of the query instead of an error.
                interpretation = f"The data at the reference '{data_reference}' for pointer '{pointer_address}' is currently unavailable or invalid."
                details = f"This pointer is intended to connect to an external resource. The attempt to access it failed, likely due to a network issue, an invalid URL, or improperly formatted data. The error was: {str(e)}"
                return {
                    "status": "interpretation_rendered",
                    "result": {"interpretation": interpretation, "details": details}
                }

            self.audit_module.log(action=query.get("action"),
                                  details=f"Connection {connection_id} accessed data for pointer {pointer_address}")
            return {
                "status": "success",
                "result": {"message": "Invocation successful. Connection has accessed the data.", "data": data_payload, "render_hint": render_hint}
            }

    def _handle_get_pointers_for_connection(self, query: dict) -> dict:
            connection_id = query.get("connection_id")
            requesting_app_id = query.get("app_id")  # From JWT
            if not connection_id or not requesting_app_id:
                return {"status": "error", "message": "Action 'get_pointers_for_connection' requires 'connection_id' and 'app_id'."}

            cursor = self.audit_module.get_cursor()
            # Verify ownership and then get pointers
            cursor.execute("SELECT p.* FROM pointers p JOIN connections c ON p.connection_id = c.id JOIN domains d ON c.domain_id = d.id WHERE p.connection_id = ? AND d.owner_app_id = ?",
                           (connection_id, requesting_app_id))
            rows = cursor.fetchall()

            pointers_list = []
            for row in rows:
                pointer_data = {
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
            search_term = query.get("search_term")  # For description
            # For a list of tags to include
            search_tags = query.get("search_tags")
            exclude_tags = query.get("exclude_tags")
            tag_match_mode = query.get("tag_match_mode", "ALL").upper()

            if not search_term and not search_tags:
                return {"status": "error", "message": "Action 'search_pointers' requires at least a 'search_term' or 'search_tags'."}

            where_clauses = []
            params = []

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
                    any_clause = " OR ".join(
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
            sql_query = """
                SELECT p.address, p.description, p.data_reference, p.tags, p.connection_id, p.x, p.y, p.z, p.created_at, p.last_modified
                FROM pointers p
            """
            if where_clauses:
                sql_query += " WHERE " + " AND ".join(where_clauses)

            cursor = self.audit_module.get_cursor()
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()

            # No iteration needed here. The data is already fetched.
            matching_pointers = [{
                "address": row[0], "description": row[1], "data_reference": row[2],
                "tags": json.loads(row[3]), "connection_id": row[4],
                "x": row[5], "y": row[6], "z": row[7],
                "created_at": row[8], "last_modified": row[9]
            } for row in rows]

            # --- Cycle Module Integration ---
            # A search returning many results is considered less "optimal"
            # because it has a higher processing cost.
            is_search_optimal = len(matching_pointers) < 50
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
            origin_pointer_address = query.get("origin_pointer_address")
            radius = query.get("radius")

            if not origin_pointer_address or radius is None:
                return {"status": "error", "message": "Action 'search_by_proximity' requires 'origin_pointer_address' and 'radius'."}

            cursor = self.audit_module.get_cursor()

            # 1. Get the coordinates of the origin pointer. This is a single, fast lookup.
            cursor.execute(
                "SELECT x, y, z FROM pointers WHERE address = ?", (origin_pointer_address,))
            origin_row = cursor.fetchone()
            if not origin_row:
                return {"status": "error", "message": f"Origin pointer not found: {origin_pointer_address}"}
            ox, oy, oz = origin_row

            # 2. Perform a native mathematical search.
            # This query calculates the squared Euclidean distance directly in the database,
            # which is highly efficient. It avoids iterating through pointers in the application.
            # We use squared distance to avoid the expensive SQRT() function in the DB.
            radius_squared = float(radius) ** 2
            # This single query fetches all necessary data, removing the need for a loop.
            cursor.execute("""
                SELECT address, description, data_reference, tags, connection_id, x, y, z, created_at, last_modified
                FROM pointers
                WHERE ((x - ?) * (x - ?)) + ((y - ?) * (y - ?)) + ((z - ?) * (z - ?)) <= ?
                AND address != ?
            """, (ox, ox, oy, oy, oz, oz, radius_squared, origin_pointer_address))

            rows = cursor.fetchall()
            matching_pointers = [{
                "address": row[0], "description": row[1], "data_reference": row[2],
                "tags": json.loads(row[3]), "connection_id": row[4],
                "x": row[5], "y": row[6], "z": row[7],
                "created_at": row[8], "last_modified": row[9]
            } for row in rows]

            return {"status": "success", "result": {"count": len(matching_pointers), "pointers": matching_pointers}}


    def _handle_get_graph_stats(self, query: dict) -> dict:
            cursor = self.audit_module.get_cursor()
            cursor.execute("SELECT COUNT(*) FROM pointers")
            num_pointers = cursor.fetchone()[0]

            # Count relationships by dividing the total rows in the relationships table by 2 (for bidirectional links)
            cursor.execute("SELECT COUNT(*) FROM relationships")
            num_relationships = cursor.fetchone()[0] // 2

            stats = {
                "total_pointers": num_pointers,
                "total_relationships": num_relationships
            }

            return {
                "status": "success",
                "result": stats
            }

    def _handle_get_admin_overview(self, query: dict) -> dict:
            requesting_app_id = query.get("app_id")  # From JWT
            if not requesting_app_id:
                return {"status": "error", "message": "Action 'get_admin_overview' requires an authenticated 'app_id'."}

            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT id, name, created_at FROM domains WHERE owner_app_id = ?", (requesting_app_id,))
            domains = [{"id": row[0], "name": row[1], "created_at": row[2], "connections": []}
                       for row in cursor.fetchall()]

            for domain in domains:
                cursor.execute(
                    "SELECT id, name, description, allow_writes FROM connections WHERE domain_id = ?", (domain['id'],))
                for conn_row in cursor.fetchall():
                    domain["connections"].append(
                        {"id": conn_row[0], "name": conn_row[1], "description": conn_row[2], "status": "read-write" if conn_row[3] == 1 else "read-only"})

            return {"status": "success", "result": {"domains": domains}}

    def _handle_get_graph_dot(self, query: dict) -> dict:
            # Start building the DOT language string. 'graph' for undirected edges.
            dot_string = 'graph G {\n    node [shape=box, style="rounded,filled", fillcolor=lightyellow];\n'

            # Keep track of edges to avoid duplicates in an undirected graph.
            drawn_edges = set()

            cursor = self.audit_module.get_cursor()
            all_pointers_res = cursor.execute(
                "SELECT address, description FROM pointers").fetchall()
            all_relationships_res = cursor.execute(
                "SELECT pointer_a_address, pointer_b_address, relationship, weight FROM relationships").fetchall()

            for row in all_pointers_res:
                address, description = row

                # Add a node for each pointer.
                description = description.replace(
                    '"', '\\"') if description else address
                dot_string += f'    "{address}" [label="{description}"];\n'

            for row in all_relationships_res:
                address, neighbor_address, relationship, weight = row
                # Add edges for each neighbor relationship.

                # To avoid duplicates, create a sorted tuple of the pair.
                edge = tuple(sorted((address, neighbor_address)))
                if edge not in drawn_edges:
                    attributes = []
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
            pointer_address = query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'get_pointer_summary' requires a 'pointer_address'."}

            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT description, tags, created_at, last_modified, connection_id, x, y, z FROM pointers WHERE address = ?", (pointer_address,))
            row = cursor.fetchone()

            if not row:
                return {"status": "error", "message": f"Pointer not found: {pointer_address}"}

            description, tags_json, created_at, last_modified, connection_id, x, y, z = row
            tags = json.loads(tags_json)

            # Get neighbor count from the new table
            cursor.execute(
                "SELECT COUNT(*) FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
            neighbor_count = cursor.fetchone()[0]

            summary = {
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
            pointer_address = query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'execute_creation_model' requires a 'pointer_address'."}

            op_id = f"op_{uuid.uuid4().hex[:8]}"
            # --- Step 1: "Let there be Light" - The Invocation ---
            # The process begins with a single query, the initial spark.
            self.cycle_module.start_cycle(op_id)
            self.audit_module.log(
                "creation_model_step1", f"Invocation received for {pointer_address}. Operation ID: {op_id}")

            # --- Step 2: "Let there be an Idea" - The Determination Graph ---
            # The "idea" is the pointer itself and its immediate context (neighbors).
            # This is the first "vertical" step, adding/multiplying context.
            graph_response = self.invoke(
                {"action": "get_pointer", "pointer_address": pointer_address})
            determination_graph = {
                "root": graph_response.get("result"),
                "neighbors": graph_response.get("result", {}).get("neighbors", [])
            }
            root_pointer = determination_graph["root"]
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step2", f"Determined local graph for {pointer_address}.")

            # --- Step 3: "Let there be Connection" - The Logic Gate ---
            # We apply logical rules, like a "horizontal" step (dividing/subtracting) to filter or test the idea.
            data_ref = root_pointer.get(
                "data_reference", "") if root_pointer else ""
            is_secure_url = data_ref.startswith("https://")
            has_connection = root_pointer.get(
                "connection_id") is not None if root_pointer else False
            has_public_tag = "public" in root_pointer.get(
                "tags", []) if root_pointer else False
            logic_gate_result = {
                "is_secure_url": is_secure_url,
                "is_public_and_connected": has_connection and has_public_tag
            }
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step3", f"Logic gate check for {pointer_address}: {logic_gate_result}")

            # --- Step 4: The Decision Tree ---
            # The sum of the previous steps allows for a higher-level decision.
            risk_level = "low"
            if not logic_gate_result["is_public_and_connected"]:
                risk_level = "high"  # Fails security gate
            elif root_pointer and root_pointer.get("z", 0) > 5:
                risk_level = "medium"  # High number of deltas/versions
            decision_tree_result = {"risk_level": risk_level}
            self.cycle_module.advance_cycle(op_id)
            self.audit_module.log(
                "creation_model_step4", f"Decision tree result for {pointer_address}: {decision_tree_result}")

            # --- Step 5: The Fibonacci Spiral - Proximity Analysis ---
            # We expand context by finding conceptually close pointers in the 3D space,
            # representing the compounding growth of the Fibonacci spiral.
            proximity_results = []
            # Ensure coordinates exist
            if root_pointer and root_pointer.get('x') is not None:
                ox, oy, oz = root_pointer.get('x', 0), root_pointer.get(
                    'y', 0), root_pointer.get('z', 0)
                radius_squared = 5.0 ** 2
                cursor.execute("""
                    SELECT address, description FROM pointers
                    WHERE ((x - ?) * (x - ?)) + ((y - ?) * (y - ?)) + ((z - ?) * (z - ?)) <= ?
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
            presentation_data = {
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
            cycle_end_status = self.cycle_module.advance_cycle(op_id)
            final_render = {
                "status": "creation_model_complete",
                "result": presentation_data,
                "_cycle_status": cycle_end_status
            }
            self.audit_module.log(
                "creation_model_step7", f"Self-reflection complete for {pointer_address}. {cycle_end_status.get('status')}")

            # As part of the final step, we can create a shortcut to this entire process.
            # Create a data_reference that encapsulates the entire circuit call.
            circuit_data_reference = f"internal_circuit::{json.dumps({'action': 'execute_creation_model', 'pointer_address': pointer_address})}"
            cursor = self.audit_module.get_cursor()
            cursor.execute(
                "SELECT address FROM pointers WHERE data_reference = ?", (circuit_data_reference,))
            existing_shortcut = cursor.fetchone()

            if existing_shortcut:
                shortcut_address = existing_shortcut[0]
                final_render["result"]["shortcut_pointer_address"] = shortcut_address
                self.audit_module.log(
                    "circuit_pointer_exists", f"Shortcut pointer {shortcut_address} already exists for this circuit.")
            else:
                shortcut_description = f"Circuit for '{pointer_address}'"
                # Use the internal `create_pointer` logic to create the shortcut
                shortcut_query = {
                    "action": "create_pointer",
                    "data_reference": circuit_data_reference,
                    "description": shortcut_description
                }
                create_response = self.invoke(shortcut_query)
                final_render["result"]["shortcut_pointer_address"] = create_response.get(
                    "result", {}).get("pointer", {}).get("address")

            return final_render

    def _handle_unrefactored_action(self, query: dict) -> dict:
        if query.get("action") == "clear_audit_log":
            requesting_app_id = query.get("app_id")  # From JWT
            admin_app_id = _config.get("admin_app_id")

            if not admin_app_id:
                return {"status": "error", "message": "Action 'clear_audit_log' is disabled because no 'admin_app_id' is configured."}

            if requesting_app_id != admin_app_id:
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}

            try:
                cursor = self.audit_module.get_cursor()
                cursor.execute("DELETE FROM audit_log")
                self.audit_module.commit()
                # Log the clear action itself as the first new entry
                self.audit_module.log("clear_audit_log", f"Audit log cleared by admin app '{requesting_app_id}'.")
                return {"status": "success", "result": {"message": "Audit log has been cleared."}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while clearing the audit log: {str(e)}"}

        elif query.get("action") == "get_all_tags":
            try:
                cursor = self.audit_module.get_cursor()
                cursor.execute("SELECT tags FROM pointers")
                rows = cursor.fetchall()
                
                all_tags = set()
                for row in rows:
                    if row[0]: # Ensure the tags column is not null
                        try:
                            tags_list = json.loads(row[0])
                            if isinstance(tags_list, list):
                                all_tags.update(tags_list)
                        except (json.JSONDecodeError, TypeError):
                            # Ignore malformed JSON in the tags column for this row
                            continue
                
                sorted_tags = sorted(list(all_tags))
                self.audit_module.log("get_all_tags", f"Retrieved {len(sorted_tags)} unique tags.")
                return {"status": "success", "result": {"tags": sorted_tags}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching tags: {str(e)}"}

        elif query.get("action") == "get_unassigned_pointers":
            # This is an administrative action. Check for admin privileges.
            requesting_app_id = query.get("app_id")  # From JWT
            admin_app_id = _config.get("admin_app_id")

            if not admin_app_id:
                return {"status": "error", "message": "Action 'get_unassigned_pointers' is disabled because no 'admin_app_id' is configured."}

            if requesting_app_id != admin_app_id:
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}

            try:
                cursor = self.audit_module.get_cursor()
                # Find all pointers where connection_id is NULL
                cursor.execute("SELECT address, description, created_at FROM pointers WHERE connection_id IS NULL")
                rows = cursor.fetchall()
                
                unassigned_pointers = [{"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]
                
                self.audit_module.log("get_unassigned_pointers", f"Found {len(unassigned_pointers)} unassigned pointers.")
                return {"status": "success", "result": {"pointers": unassigned_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching unassigned pointers: {str(e)}"}

        elif query.get("action") == "get_available_apis":
            try:
                edition = os.environ.get('BUTTERFLY_EDITION', 'COMMUNITY').upper()
                # The _get_predefined_api method is designed to get a single API.
                # We can introspect it to build the full list.
                # This is a simplified way to get the source dictionaries.
                all_apis = self._get_predefined_api(None) # This will be the full dict for the edition
                
                # Format for client consumption
                available_apis = [{"api_type": key, "description": value["description"]} for key, value in all_apis.items()]
                
                return {"status": "success", "result": {"edition": edition, "available_apis": available_apis}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching available APIs: {str(e)}"}

        elif query.get("action") == "find_pointers_by_tag":
            tag = query.get("tag")
            if not tag:
                return {"status": "error", "message": "Action 'find_pointers_by_tag' requires a 'tag'."}

            try:
                cursor = self.audit_module.get_cursor()
                # Use LIKE to find the tag within the JSON array string
                # The quotes ensure we match the whole tag string, e.g., "user_data"
                cursor.execute("SELECT address, description, created_at FROM pointers WHERE tags LIKE ?", (f'%"{tag}"%',))
                rows = cursor.fetchall()

                matching_pointers = [{"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]

                self.audit_module.log("find_pointers_by_tag", f"Found {len(matching_pointers)} pointers with tag '{tag}'.")
                return {"status": "success", "result": {"pointers": matching_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while finding pointers by tag: {str(e)}"}

        elif query.get("action") == "get_pointer_relationships":
            pointer_address = query.get("pointer_address")
            if not pointer_address:
                return {"status": "error", "message": "Action 'get_pointer_relationships' requires a 'pointer_address'."}

            try:
                cursor = self.audit_module.get_cursor()
                # Use DISTINCT to get a unique list of relationship types for the pointer
                cursor.execute("SELECT DISTINCT relationship FROM relationships WHERE pointer_a_address = ?", (pointer_address,))
                rows = cursor.fetchall()

                # Extract the relationship strings from the query result
                relationship_types = [row[0] for row in rows if row[0]]

                self.audit_module.log("get_pointer_relationships", f"Found {len(relationship_types)} unique relationship types for pointer '{pointer_address}'.")
                return {"status": "success", "result": {"relationships": sorted(relationship_types)}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching pointer relationships: {str(e)}"}

        elif query.get("action") == "get_isolated_pointers":
            # This is an administrative action. Check for admin privileges.
            requesting_app_id = query.get("app_id")  # From JWT
            admin_app_id = _config.get("admin_app_id")

            if not admin_app_id:
                return {"status": "error", "message": "Action 'get_isolated_pointers' is disabled because no 'admin_app_id' is configured."}

            if requesting_app_id != admin_app_id:
                return {"status": "error", "message": "Access denied. This action requires administrative privileges."}

            try:
                cursor = self.audit_module.get_cursor()
                # Use a LEFT JOIN to find pointers that have no entries in the relationships table.
                cursor.execute("""
                    SELECT p.address, p.description, p.created_at
                    FROM pointers p
                    LEFT JOIN relationships r ON p.address = r.pointer_a_address
                    WHERE r.pointer_a_address IS NULL
                """)
                rows = cursor.fetchall()
                isolated_pointers = [{"address": row[0], "description": row[1], "created_at": row[2]} for row in rows]
                self.audit_module.log("get_isolated_pointers", f"Found {len(isolated_pointers)} isolated pointers.")
                return {"status": "success", "result": {"pointers": isolated_pointers}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching isolated pointers: {str(e)}"}

        elif query.get("action") == "get_relationships_by_type":
            relationship_type = query.get("relationship_type")
            if not relationship_type:
                return {"status": "error", "message": "Action 'get_relationships_by_type' requires a 'relationship_type'."}

            try:
                cursor = self.audit_module.get_cursor()
                # Query for relationships of a specific type.
                # The pointer_a_address < pointer_b_address condition prevents duplicates from the bidirectional links.
                cursor.execute("SELECT pointer_a_address, pointer_b_address, weight FROM relationships WHERE relationship = ? AND pointer_a_address < pointer_b_address", (relationship_type,))
                rows = cursor.fetchall()

                relationships = [{"pointer_a": row[0], "pointer_b": row[1], "weight": row[2]} for row in rows]

                self.audit_module.log("get_relationships_by_type", f"Found {len(relationships)} relationships of type '{relationship_type}'.")
                return {"status": "success", "result": {"relationships": relationships}}
            except Exception as e:
                return {"status": "error", "message": f"An error occurred while fetching relationships by type: {str(e)}"}

        else:
            return {"status": "error", "message": f"Unknown action: '{query.get('action')}'"}


# --- Flask Web Server Setup ---
# This provides the API endpoint for applications to interact with the PointerHelper.
app = Flask(__name__)
CONFIG_FILE = 'config.json'
# Enables Cross-Origin Resource Sharing (CORS) to allow web apps to call this API.
CORS(app)

# Instantiate our one and only PointerHelper for the Community Edition.
butterfly_helper = None # Will be initialized after config is loaded

# --- Caching for Report Endpoint ---
_report_cache = {}
# Cache reports for 5 minutes. A real implementation detail.
CACHE_TTL_SECONDS = 300

# --- JWT Authentication Setup ---

# It's critical to load this from an environment variable in production.
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-super-secret-key-for-dev')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            # Passthrough mode for external authentication (e.g., reverse proxy)
            auth_mode = _config.get('authentication_mode', 'internal')
            if auth_mode == 'passthrough':
                return f({'app_id': 'passthrough_user'}, *args, **kwargs)

            # Expected format: "Bearer <token>"
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Bearer token malformed.'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decode the token using the app's secret key
            payload = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # The payload itself is the credential. We just need to ensure it has the app_id.
            if 'app_id' not in payload:
                return jsonify({'message': 'Token is invalid! Missing app_id.'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(payload, *args, **kwargs)
    return decorated


@app.route('/invoke', methods=['POST'])
@token_required
# token_payload is now passed from the decorator
def handle_invocation(token_payload):
    encrypted_query_str = request.data.decode('utf-8')
    try:
        query = butterfly_helper.encryption_module.decrypt(encrypted_query_str)
        # Inject the app_id from the token into the query for permission checks
        query['app_id'] = token_payload['app_id']
        response = butterfly_helper.invoke(query)
        encrypted_response = butterfly_helper.encryption_module.encrypt(
            response)
        return encrypted_response, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return butterfly_helper.encryption_module.encrypt({"status": "error", "message": f"Failed to process encrypted request: {str(e)}"}), 400, {'Content-Type': 'text/plain'}


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """
    Exposes the list of pre-defined API connections the server offers.
    """
    # This endpoint can now use the same logic as the API action
    api_definitions = butterfly_helper._get_predefined_api(None) # Gets the full dictionary
    if api_definitions:
        return jsonify(api_definitions)
    return jsonify({})


@app.route('/report', methods=['GET'])
def generate_report():
    """
    Generates a live report by invoking a predefined API connection,
    with a simple in-memory cache to avoid excessive API calls.
    """
    api_type = request.args.get('type')
    if not api_type:
        return jsonify({"error": "API type parameter is missing"}), 400

    # Check cache first
    current_time = time.time()
    if api_type in _report_cache and (current_time - _report_cache[api_type]['timestamp']) < CACHE_TTL_SECONDS:
        print(f"[*] Serving report for '{api_type}' from cache.")
        return jsonify(_report_cache[api_type]['data'])

    print(
        f"[*] Generating new report for '{api_type}'. Cache miss or expired.")
    api_info = butterfly_helper._get_predefined_api(api_type)
    if not api_info:
        return jsonify({"error": "Invalid API type"}), 404

    try:
        response = requests.get(api_info['data_reference'], timeout=10)
        response.raise_for_status()
        data_payload = response.json()
        report_data = {"source": api_info['description'], "data": data_payload}

  
        # Store the new report in the cache
        _report_cache[api_type] = {
            'timestamp': current_time, 'data': report_data}
        return jsonify(report_data)
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return jsonify({"error": f"Failed to fetch or parse data from API: {str(e)}"})


@app.route('/')
def index():
    # Serve the main landing page.
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'landing.html')


@app.route('/subscribe', methods=['POST'])
def subscribe():
    """Handles mailing list subscription form submissions."""
    email = request.form.get('email')
    if not email:
        return "Email address is required.", 400

    try:
        cursor = butterfly_helper.audit_module.get_cursor()
        timestamp = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO mailing_list (email, subscribed_at) VALUES (?, ?)",
                       (email, timestamp))
        butterfly_helper.audit_module.commit()
        return "<h3>Subscription Successful!</h3><p>Thank you for subscribing. You've been added to the mailing list for updates and patches.</p><a href='/'>Return Home</a>", 200
    except sqlite3.IntegrityError:
        # This error occurs if the email is not unique.
        return "<h3>Already Subscribed</h3><p>This email address is already on our mailing list.</p><a href='/'>Return Home</a>", 200
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


def run_setup_wizard():
    """A simple CLI wizard to configure the app on first run."""
    print("--- Butterfly System Setup Wizard ---")
    print("This will create a 'config.json' file to store your settings.")

    # 1. Configure Database
    db_choice = input("Use default SQLite database (butterfly_local.db)? [Y/n]: ").lower().strip()
    if db_choice == 'n':
        db_path = input("Enter the full path for your SQLite database file: ").strip()
    else:
        db_path = "butterfly_local.db"

    # 2. Configure Authentication
    print("\nSelect Authentication Mode:")
    print("1. Internal (Default): The server will manage JWTs for secure access.")
    print("2. Passthrough: The server will bypass JWT validation. Use this only if you are running this service behind a reverse proxy that handles authentication.")
    auth_choice = input("Enter your choice [1]: ").strip()
    if auth_choice == '2':
        auth_mode = 'passthrough'
        print("\n[!] WARNING: Passthrough mode is insecure if the server is exposed directly to the internet.")
    else:
        auth_mode = 'internal'

    # 3. Configure Admin App ID
    admin_id_choice = input("\nSet a special App ID for administrative actions (e.g., clearing logs)? [y/N]: ").lower().strip()
    admin_app_id = None
    if admin_id_choice == 'y':
        admin_app_id = input("Enter the admin App ID: ").strip()

    config_data = {
        "database_path": db_path,
        "authentication_mode": auth_mode,
        "admin_app_id": admin_app_id
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

    print(f"\nConfiguration saved to '{CONFIG_FILE}'. You can delete this file to run the wizard again.")
    return config_data


def load_config():
    """Loads configuration from file or runs the setup wizard."""
    if not os.path.exists(CONFIG_FILE):
        return run_setup_wizard()
    else:
        with open(CONFIG_FILE, 'r') as f:
            print(f"[*] Loading configuration from '{CONFIG_FILE}'.")
            return json.load(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Butterfly Server and Admin CLI.")
    parser.add_argument('--create-domain', nargs=2, metavar=('APP_ID', 'DOMAIN_NAME'),
                        help='Create a new domain for a given app ID.')
    parser.add_argument('--create-api-connection', nargs=3, metavar=('DOMAIN_ID', 'CONN_NAME', 'API_TYPE'),
                        help='Create a pre-defined API connection (e.g., weather, news).')
    parser.add_argument('--list-domains', metavar='APP_ID',
                        help='List all domains for a given app ID.')
    parser.add_argument('--export-mailing-list', metavar='CSV_FILE_PATH',
                        help='Export the mailing list to a CSV file.')
    parser.add_argument('--view-audit-log', nargs='?', const=25, type=int, metavar='LIMIT',
                        help='View the most recent audit log entries. Defaults to 25 if no limit is given.')
    parser.add_argument('--backup-database', metavar='BACKUP_FILE_PATH',
                        help='Create a backup of the application database.')
    parser.add_argument('--delete-pointer', metavar='POINTER_ADDRESS',
                        help='Permanently delete a pointer from the system.')
    parser.add_argument('--delete-domain', metavar='DOMAIN_ID',
                        help='Permanently delete a domain and its connections. Pointers will be unassigned.')
    parser.add_argument('--merge-domains', nargs=2, metavar=('SOURCE_ID', 'DEST_ID'),
                        help='Merge all connections from source domain into destination domain, then delete source domain.')
    parser.add_argument('--cleanup-orphaned-pointers', action='store_true',
                        help='Find and permanently delete all pointers not assigned to any connection.')

    args = parser.parse_args()

    # Load config or run wizard before initializing the helper
    _config = load_config()
    butterfly_helper = PointerHelper()

    if args.create_domain:
        app_id, domain_name = args.create_domain
        print(
            f"Executing admin command: Create Domain for App ID '{app_id}' with name '{domain_name}'")

        # Use the global helper instance to access the database module
        query = {
            "action": "create_domain",
            "owner_app_id": app_id,
            "name": domain_name
        }
        result = butterfly_helper.invoke(query)
        print(json.dumps(result, indent=2))

    elif args.create_api_connection:
        domain_id, conn_name, api_type = args.create_api_connection
        print(
            f"Executing admin command: Create API Connection in Domain '{domain_id}' with name '{conn_name}' of type '{api_type}'")
        query = {
            "action": "create_connection",
            "domain_id": domain_id,
            "name": conn_name,
            "api_type": api_type
        }
        result = butterfly_helper.invoke(query)
        print(json.dumps(result, indent=2))

    elif args.list_domains:
        app_id = args.list_domains
        print(f"Executing admin command: List Domains for App ID '{app_id}'")
        # This uses a direct DB query as it's a pure admin function.
        cursor = butterfly_helper.audit_module.get_cursor()
        cursor.execute(
            "SELECT id, name, created_at FROM domains WHERE owner_app_id = ?", (app_id,))
        domains = [{"id": row[0], "name": row[1], "created_at": row[2]}
                   for row in cursor.fetchall()]
        if not domains:
            print(f"No domains found for App ID: {app_id}")
        else:
            print(json.dumps({"domains": domains}, indent=2))

    elif args.export_mailing_list:
        filepath = args.export_mailing_list
        print(f"[*] Executing admin command: Export mailing list to '{filepath}'")
        try:
            cursor = butterfly_helper.audit_module.get_cursor()
            cursor.execute("SELECT email, subscribed_at FROM mailing_list ORDER BY subscribed_at")
            rows = cursor.fetchall()

            if not rows:
                print("Mailing list is empty. No file created.")
            else:
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['email', 'subscribed_at'])  # Write header
                    writer.writerows(rows)  # Write data
                print(f"[*] Successfully exported {len(rows)} email(s) to {filepath}")
        except Exception as e:
            print(f"[!] An error occurred during export: {e}")

    elif args.view_audit_log:
        limit = args.view_audit_log
        print(f"[*] Executing admin command: View last {limit} audit log entries")
        try:
            cursor = butterfly_helper.audit_module.get_cursor()
            cursor.execute("SELECT timestamp, action, details FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()

            if not rows:
                print("Audit log is empty.")
            else:
                print("-" * 80)
                print(f"{'Timestamp':<30} {'Action':<25} {'Details'}")
                print("-" * 80)
                for row in reversed(rows): # Reverse to show oldest first in the selection
                    timestamp, action, details = row
                    details_short = (details[:75] + '...') if len(details) > 78 else details
                    print(f"{timestamp:<30} {action:<25} {details_short}")
                print("-" * 80)
        except Exception as e:
            print(f"[!] An error occurred while fetching the audit log: {e}")

    elif args.backup_database:
        backup_path = args.backup_database
        source_db_path = _config.get('database_path', 'butterfly_local.db')
        print(f"[*] Executing admin command: Back up database to '{backup_path}'")
        try:
            # Ensure the source database exists before trying to back it up
            if not os.path.exists(source_db_path):
                print(f"[!] Error: Source database not found at '{source_db_path}'")
            else:
                shutil.copyfile(source_db_path, backup_path)
                print(f"[*] Backup successful. Database saved to '{backup_path}'")
        except Exception as e:
            print(f"[!] An error occurred during backup: {e}")

    elif args.delete_pointer:
        pointer_address = args.delete_pointer
        print(f"[*] Executing admin command: Delete pointer '{pointer_address}'")
        print("[!] WARNING: This is a destructive and irreversible action. Deleting a pointer will also remove all its relationships.")
        
        confirm = input("    Are you sure you want to proceed? [y/N]: ").lower().strip()
        if confirm == 'y':
            try:
                cursor = butterfly_helper.audit_module.get_cursor()
                cursor.execute("DELETE FROM pointers WHERE address = ?", (pointer_address,))
                butterfly_helper.audit_module.commit()
                
                if cursor.rowcount > 0:
                    print(f"[*] Pointer '{pointer_address}' has been deleted successfully.")
                    butterfly_helper.audit_module.log("delete_pointer", f"Admin deleted pointer {pointer_address}.")
                else:
                    print(f"[*] Pointer '{pointer_address}' not found.")
            except Exception as e:
                print(f"[!] An error occurred during deletion: {e}")
        else:
            print("Deletion cancelled.")

    elif args.delete_domain:
        domain_id = args.delete_domain
        print(f"[*] Executing admin command: Delete domain '{domain_id}'")
        print("[!] WARNING: This will permanently delete the domain and all its connections.")
        print("[!] Pointers assigned to these connections will be orphaned (unassigned).")

        confirm = input("    Are you sure you want to proceed? [y/N]: ").lower().strip()
        if confirm == 'y':
            try:
                cursor = butterfly_helper.audit_module.get_cursor()

                # Find connections to be deleted
                cursor.execute("SELECT id FROM connections WHERE domain_id = ?", (domain_id,))
                connection_ids = [row[0] for row in cursor.fetchall()]

                if connection_ids:
                    # Un-assign pointers from these connections
                    placeholders = ','.join('?' for _ in connection_ids)
                    cursor.execute(f"UPDATE pointers SET connection_id = NULL WHERE connection_id IN ({placeholders})", connection_ids)
                    print(f"[*] Unassigned {cursor.rowcount} pointer(s).")

                    # Delete the connections
                    cursor.execute(f"DELETE FROM connections WHERE domain_id = ?", (domain_id,))
                    print(f"[*] Deleted {cursor.rowcount} connection(s).")

                # Delete the domain
                cursor.execute("DELETE FROM domains WHERE id = ?", (domain_id,))
                print(f"[*] Deleted {cursor.rowcount} domain(s).")

                butterfly_helper.audit_module.commit()
                print(f"[*] Domain '{domain_id}' and its contents have been deleted successfully.")
            except Exception as e:
                print(f"[!] An error occurred during domain deletion: {e}")
        else:
            print("Deletion cancelled.")

    elif args.merge_domains:
        source_id, dest_id = args.merge_domains
        print(f"[*] Executing admin command: Merge domain '{source_id}' into '{dest_id}'")
        print("[!] WARNING: This will move all connections from the source domain to the destination and permanently delete the source domain.")

        confirm = input("    Are you sure you want to proceed? [y/N]: ").lower().strip()
        if confirm == 'y':
            try:
                cursor = butterfly_helper.audit_module.get_cursor()

                # Verify both domains exist
                cursor.execute("SELECT COUNT(*) FROM domains WHERE id IN (?, ?)", (source_id, dest_id))
                if cursor.fetchone()[0] != 2:
                    print("[!] Error: One or both domains not found. Merge cancelled.")
                else:
                    # Re-assign all connections from the source domain to the destination domain
                    cursor.execute("UPDATE connections SET domain_id = ? WHERE domain_id = ?", (dest_id, source_id))
                    print(f"[*] Re-assigned {cursor.rowcount} connection(s) to domain '{dest_id}'.")

                    # Delete the now-empty source domain
                    cursor.execute("DELETE FROM domains WHERE id = ?", (source_id,))
                    
                    butterfly_helper.audit_module.commit()
                    print(f"[*] Source domain '{source_id}' has been deleted. Merge complete.")
                    butterfly_helper.audit_module.log("merge_domains", f"Admin merged domain {source_id} into {dest_id}.")
            except Exception as e:
                print(f"[!] An error occurred during domain merge: {e}")
        else:
            print("Merge cancelled.")

    elif args.cleanup_orphaned_pointers:
        print("[*] Executing admin command: Find and delete orphaned pointers.")
        print("[!] WARNING: This will permanently delete all pointers that are not assigned to any connection.")

        confirm = input("    Are you sure you want to proceed? [y/N]: ").lower().strip()
        if confirm == 'y':
            try:
                cursor = butterfly_helper.audit_module.get_cursor()
                # Find and delete all pointers where connection_id is NULL
                cursor.execute("DELETE FROM pointers WHERE connection_id IS NULL")
                num_deleted = cursor.rowcount
                butterfly_helper.audit_module.commit()

                print(f"[*] Cleanup complete. Deleted {num_deleted} orphaned pointer(s).")
                if num_deleted > 0:
                    butterfly_helper.audit_module.log("cleanup_orphaned_pointers", f"Admin deleted {num_deleted} orphaned pointers.")
            except Exception as e:
                print(f"[!] An error occurred during cleanup: {e}")
        else:
            print("Merge cancelled.")
    else:
        # If no admin commands are given, run the server
        print("Starting Butterfly server...")
        # In a production Docker environment, gunicorn is used. This is for local dev.
        # debug=False for production-like behavior
        app.run(host='0.0.0.0', port=5001, debug=False)
