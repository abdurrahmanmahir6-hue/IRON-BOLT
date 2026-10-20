"""
Short-Term Memory Implementation

Handles temporary, session-based memories with TTL expiry.
Used for: recent conversation context, temporary facts, current task state.
"""

from typing import Optional, Any, List
from datetime import datetime, timedelta

from .base_memory import BaseMemory
from .models import MemoryEntry, MemoryType, MemoryImportance
from .storage import BaseStorageBackend, create_storage_backend
from .config import MemoryConfig, get_memory_config
from .exceptions import MemoryError


class ShortTermMemory(BaseMemory):
    """
    Short-term memory implementation.

    Characteristics:
    - Temporary storage with TTL (Time-To-Live)
    - Automatically expires after configured duration
    - Used for immediate context and recent interactions
    - Higher capacity than long-term memory
    """

    def __init__(
        self,
        storage: BaseStorageBackend,
        user_id: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
    ):
        """
        Initialize short-term memory.

        Args:
            storage: Storage backend instance
            user_id: Optional user ID for filtering
            config: Memory configuration
        """
        super().__init__(MemoryType.SHORT_TERM, user_id)
        self._storage = storage
        self._config = config or get_memory_config()
        self._ttl_seconds = self._config.ttl_seconds

    def save(self, entry: MemoryEntry) -> bool:
        """Save a short-term memory entry."""
        if entry.memory_type != self._memory_type:
            entry.memory_type = self._memory_type

        # Set expiry if not already set
        if entry.expires_at is None and self._ttl_seconds:
            from .utils import generate_expiry_timestamp
            entry.expires_at = generate_expiry_timestamp(self._ttl_seconds)

        return self._storage.save(entry)

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        entry = self._storage.get(memory_id)
        if entry and not entry.is_expired():
            entry.touch()
            return entry
        return None

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self._storage.delete(memory_id)

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search for memories."""
        # Add memory_type filter
        if filters is None:
            filters = {}
        filters["memory_type"] = self._memory_type

        if self._user_id:
            filters["user_id"] = self._user_id

        return self._storage.search(query=query, filters=filters, limit=limit)

    def update(self, memory_id: str, **kwargs) -> Optional[MemoryEntry]:
        """Update a memory entry."""
        entry = self._storage.get(memory_id)
        if not entry:
            return None

        # Update fields
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.utcnow()
        if self._storage.update(entry):
            return entry
        return None

    def clear(self) -> bool:
        """Clear all short-term memories."""
        return self._storage.clear(memory_type=self._memory_type)

    def count(self) -> int:
        """Get count of short-term memories."""
        return self._storage.count(memory_type=self._memory_type)

    def cleanup(self) -> int:
        """
        Remove expired short-term memory entries only.

        This method specifically targets SHORT_TERM memory type entries
        and will NOT delete other memory types (long_term, user, conversation, etc.)
        even if they are expired.

        Returns:
            Number of entries removed
        """
        # Get all short-term memories for this user
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )

        # Find expired ones
        expired_ids = [e.id for e in entries if e.is_expired()]

        # Delete only expired short-term memories
        removed_count = 0
        for entry_id in expired_ids:
            if self._storage.delete(entry_id):
                removed_count += 1

        return removed_count

    def add(
        self,
        content: str,
        importance: int = 3,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        """
        Convenience method to add a new short-term memory.

        Args:
            content: Memory content
            importance: Importance score (1-5)
            metadata: Optional metadata
            tags: Optional tags
            session_id: Optional session ID

        Returns:
            Created MemoryEntry or None if failed
        """
        entry = self._create_entry(
            content=content,
            importance=importance,
            metadata=metadata,
            tags=tags,
            session_id=session_id,
        )
        if self.save(entry):
            return entry
        return None

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent short-term memories."""
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )
        # Filter expired and sort by recency
        entries = [e for e in entries if not e.is_expired()]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]