"""
IRON BOLT - Database Layer
Data persistence layer for structured data.
Architecture: Abstract database interface with concrete implementations.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import json
import os


class DatabaseInterface(ABC):
    """Abstract database interface."""

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def create(self, table: str, data: Dict[str, Any]) -> str:
        """Create a record, return ID."""
        pass

    @abstractmethod
    def read(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        pass

    @abstractmethod
    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        pass

    @abstractmethod
    def delete(self, table: str, record_id: str) -> bool:
        """Delete a record."""
        pass

    @abstractmethod
    def query(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query records with filters."""
        pass


class JSONDatabase(DatabaseInterface):
    """
    JSON file-based database for AR1.
    Simple but effective for development and small-scale use.
    """

    def __init__(self, db_path: str = "data/iron_bolt_db.json"):
        self.db_path = db_path
        self.data: Dict[str, Dict[str, Any]] = {}
        self.connected = False

    def connect(self):
        """Load database from file."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[DB Warning] Could not load DB: {e}")
                self.data = {}
        else:
            self.data = {}
        self.connected = True
        print(f"[DB] Connected to {self.db_path}")

    def disconnect(self):
        """Save database to file."""
        if self.connected:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.connected = False
            print("[DB] Disconnected and saved")

    def _ensure_table(self, table: str):
        """Ensure table exists."""
        if table not in self.data:
            self.data[table] = {}

    def create(self, table: str, data: Dict[str, Any]) -> str:
        """Create a record."""
        self._ensure_table(table)
        record_id = f"{table}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        data["_id"] = record_id
        data["_created_at"] = datetime.now().isoformat()
        data["_updated_at"] = data["_created_at"]
        self.data[table][record_id] = data
        self.disconnect()
        self.connect()
        return record_id

    def read(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record."""
        self._ensure_table(table)
        return self.data[table].get(record_id)

    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        self._ensure_table(table)
        if record_id in self.data[table]:
            self.data[table][record_id].update(data)
            self.data[table][record_id]["_updated_at"] = datetime.now().isoformat()
            self.disconnect()
            self.connect()
            return True
        return False

    def delete(self, table: str, record_id: str) -> bool:
        """Delete a record."""
        self._ensure_table(table)
        if record_id in self.data[table]:
            del self.data[table][record_id]
            self.disconnect()
            self.connect()
            return True
        return False

    def query(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query records with simple filters."""
        self._ensure_table(table)
        records = list(self.data[table].values())

        if not filters:
            return records

        results = []
        for record in records:
            match = True
            for key, value in filters.items():
                if key.startswith("_"):
                    continue
                if record.get(key) != value:
                    match = False
                    break
            if match:
                results.append(record)

        return results


class DatabaseManager:
    """
    Database Manager - central controller for database operations.
    Single Responsibility: Manage all database interactions.
    """

    def __init__(self, db: DatabaseInterface = None):
        self.db = db or JSONDatabase()
        self.connected = False

    def initialize(self):
        """Initialize database connection."""
        self.db.connect()
        self.connected = True
        print("[DatabaseManager] Initialized")

    def shutdown(self):
        """Shutdown database connection."""
        self.db.disconnect()
        self.connected = False
        print("[DatabaseManager] Shutdown")

    def save_record(self, table: str, data: Dict[str, Any]) -> str:
        """Save a record to a table."""
        return self.db.create(table, data)

    def get_record(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a record by ID."""
        return self.db.read(table, record_id)

    def update_record(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        return self.db.update(table, record_id, data)

    def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record."""
        return self.db.delete(table, record_id)

    def query_records(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query records."""
        return self.db.query(table, filters)

    def save_user(self, user_data: Dict[str, Any]) -> str:
        """Save user data."""
        return self.save_record("users", user_data)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.get_record("users", user_id)

    def save_project(self, project_data: Dict[str, Any]) -> str:
        """Save project data."""
        return self.save_record("projects", project_data)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        return self.get_record("projects", project_id)


# Singleton instance
_db_manager_instance = None

def get_database_manager(db_path: str = "data/iron_bolt_db.json") -> DatabaseManager:
    """Get or create global database manager."""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager(JSONDatabase(db_path))
    return _db_manager_instance
