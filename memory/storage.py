"""
Memory Storage Backends

Abstract base class and concrete implementations for memory storage.
Supports multiple backends: JSON file, SQLite, In-Memory, Vector (future).
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, List
from datetime import date, datetime
import json
import os
import tempfile

from .models import MemoryEntry, MemoryType, utc_now
from .exceptions import MemoryStorageError, MemoryNotFoundError
from .utils import is_expired


def _json_default(value: Any) -> Any:
    """Convert values commonly stored in memory metadata to JSON values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class BaseStorageBackend(ABC):
    """Abstract base class for all storage backends."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the storage backend."""
        pass

    @abstractmethod
    def save(self, entry: MemoryEntry) -> bool:
        """Save a memory entry."""
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass

    @abstractmethod
    def get_all(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """Get all entries, optionally filtered."""
        pass

    @abstractmethod
    def update(self, entry: MemoryEntry) -> bool:
        """Update an existing memory entry."""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search for memory entries."""
        pass

    @abstractmethod
    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """Get count of entries."""
        pass

    @abstractmethod
    def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear entries, optionally by type."""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        pass

    @abstractmethod
    def close(self) -> bool:
        """Close/cleanup the storage backend."""
        pass


class InMemoryStorage(BaseStorageBackend):
    """In-memory storage backend (for testing/development)."""

    def __init__(self):
        self._entries: dict[str, MemoryEntry] = {}
        self._initialized = False

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def save(self, entry: MemoryEntry) -> bool:
        if not self._initialized:
            raise MemoryStorageError("Storage not initialized")
        self._entries[entry.id] = entry
        return True

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(memory_id)

    def get_all(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
    ) -> list[MemoryEntry]:
        entries = list(self._entries.values())
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return entries

    def update(self, entry: MemoryEntry) -> bool:
        if entry.id not in self._entries:
            return False
        self._entries[entry.id] = entry
        return True

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._entries:
            del self._entries[memory_id]
            return True
        return False

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        results = list(self._entries.values())

        # Filter out expired entries
        results = [entry for entry in results if not entry.is_expired()]

        # Apply query filter
        if query:
            query_lower = query.lower()
            results = [
                entry
                for entry in results
                if query_lower in entry.content.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ]

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(MemoryEntry, key):
                    # Filter on MemoryEntry attribute
                    results = [
                        entry for entry in results if getattr(entry, key, None) == value
                    ]
                elif key.startswith("metadata."):
                    # Metadata filter with dot notation: metadata.key
                    metadata_key = key[len("metadata."):]
                    results = [
                        entry for entry in results
                        if entry.metadata.get(metadata_key) == value
                    ]
                else:
                    # Direct metadata field filter (for backwards compatibility)
                    results = [
                        entry for entry in results
                        if entry.metadata.get(key) == value
                    ]

        # Sort by importance (descending) then by recency
        results.sort(key=lambda entry: (entry.importance.value, entry.created_at), reverse=True)

        return results[:limit]

    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        if memory_type:
            return len(
                [e for e in self._entries.values() if e.memory_type == memory_type]
            )
        return len(self._entries)

    def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        if memory_type:
            to_delete = [
                eid for eid, e in self._entries.items() if e.memory_type == memory_type
            ]
            for eid in to_delete:
                del self._entries[eid]
        else:
            self._entries.clear()
        return True

    def cleanup_expired(self) -> int:
        expired = [eid for eid, e in self._entries.items() if e.is_expired()]
        for eid in expired:
            del self._entries[eid]
        return len(expired)

    def close(self) -> bool:
        self._entries.clear()
        self._initialized = False
        return True


class JSONStorage(BaseStorageBackend):
    """JSON file-based storage backend."""

    def __init__(self, file_path: str = "data/memory.json"):
        self._file_path = file_path
        self._entries: dict[str, MemoryEntry] = {}
        self._initialized = False

    def initialize(self) -> bool:
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(self._file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            # Load existing data if file exists
            if os.path.exists(self._file_path):
                try:
                    with open(self._file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError as exc:
                    # A process interrupted while writing the file can leave a
                    # truncated JSON document. Preserve it for recovery and
                    # start with an empty store instead of blocking startup.
                    corrupt_path = (
                        f"{self._file_path}.corrupt-"
                        f"{utc_now().strftime('%Y%m%d%H%M%S')}"
                    )
                    os.replace(self._file_path, corrupt_path)
                    self._entries.clear()
                    self._save_to_file()
                    print(
                        f"[Memory Warning] Invalid JSON in {self._file_path} "
                        f"({exc}); moved original to {corrupt_path}"
                    )
                else:
                    if not isinstance(data, dict):
                        raise ValueError("storage root must be a JSON object")
                    for entry_data in data.get("entries", []):
                        entry = MemoryEntry.from_dict(entry_data)
                        self._entries[entry.id] = entry
            else:
                # Create empty file
                self._save_to_file()

            self._initialized = True
            return True
        except Exception as e:
            raise MemoryStorageError(f"Failed to initialize JSON storage: {e}")

    def _save_to_file(self) -> bool:
        """Persist entries to JSON file."""
        try:
            data = {
                "entries": [e.to_dict() for e in self._entries.values()],
                "last_updated": utc_now().isoformat(),
            }
            directory = os.path.dirname(self._file_path) or "."
            fd, temp_path = tempfile.mkstemp(
                prefix=".memory-", suffix=".json", dir=directory
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(
                        data,
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=_json_default,
                    )
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self._file_path)
            except Exception:
                # The temporary file is safe to remove; the live file remains
                # untouched if serialization or replacement fails.
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
            return True
        except Exception as e:
            raise MemoryStorageError(f"Failed to save to JSON file: {e}")

    def save(self, entry: MemoryEntry) -> bool:
        if not self._initialized:
            raise MemoryStorageError("Storage not initialized")
        self._entries[entry.id] = entry
        return self._save_to_file()

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(memory_id)

    def get_all(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
    ) -> list[MemoryEntry]:
        entries = list(self._entries.values())
        if memory_type:
            entries = [e for e in entries if e.memory_type == memory_type]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return entries

    def update(self, entry: MemoryEntry) -> bool:
        if entry.id not in self._entries:
            return False
        self._entries[entry.id] = entry
        return self._save_to_file()

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._entries:
            del self._entries[memory_id]
            return self._save_to_file()
        return False

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        results = list(self._entries.values())

        # Filter out expired entries
        results = [entry for entry in results if not entry.is_expired()]

        # Apply query filter
        if query:
            query_lower = query.lower()
            results = [
                entry
                for entry in results
                if query_lower in entry.content.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ]

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(MemoryEntry, key):
                    # Filter on MemoryEntry attribute
                    results = [
                        entry for entry in results if getattr(entry, key, None) == value
                    ]
                elif key.startswith("metadata."):
                    # Metadata filter with dot notation: metadata.key
                    metadata_key = key[len("metadata."):]
                    results = [
                        entry for entry in results
                        if entry.metadata.get(metadata_key) == value
                    ]
                else:
                    # Direct metadata field filter (for backwards compatibility)
                    results = [
                        entry for entry in results
                        if entry.metadata.get(key) == value
                    ]

        # Sort by importance then recency
        results.sort(key=lambda entry: (entry.importance.value, entry.created_at), reverse=True)

        return results[:limit]

    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        if memory_type:
            return len(
                [e for e in self._entries.values() if e.memory_type == memory_type]
            )
        return len(self._entries)

    def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        if memory_type:
            to_delete = [
                eid for eid, e in self._entries.items() if e.memory_type == memory_type
            ]
            for eid in to_delete:
                del self._entries[eid]
        else:
            self._entries.clear()
        return self._save_to_file()

    def cleanup_expired(self) -> int:
        expired = [eid for eid, e in self._entries.items() if e.is_expired()]
        for eid in expired:
            del self._entries[eid]
        if expired:
            return len(expired)
        return 0

    def close(self) -> bool:
        if self._initialized:
            self._save_to_file()
        self._entries.clear()
        self._initialized = False
        return True


def create_storage_backend(backend_type: str, config: dict[str, Any]) -> BaseStorageBackend:
    """
    Factory function to create storage backend instances.

    Args:
        backend_type: Type of backend ('json', 'sqlite', 'in_memory')
        config: Configuration dictionary

    Returns:
        Storage backend instance
    """
    if backend_type == "json":
        return JSONStorage(file_path=config.get("storage_path", "data/memory.json"))
    elif backend_type == "in_memory":
        return InMemoryStorage()
    elif backend_type == "sqlite":
        # SQLite implementation can be added later
        raise NotImplementedError("SQLite backend not yet implemented")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
