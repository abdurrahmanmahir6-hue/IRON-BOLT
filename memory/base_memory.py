"""
Base Memory Class

Abstract base class defining the interface for all memory type implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime

from .models import MemoryEntry, MemoryType


class BaseMemory(ABC):
    """
    Abstract base class for all memory types.

    Provides common interface and shared functionality for:
    - ShortTermMemory
    - LongTermMemory
    - ConversationMemory
    - UserMemory
    - etc.
    """

    def __init__(self, memory_type: MemoryType, user_id: Optional[str] = None):
        """
        Initialize base memory.

        Args:
            memory_type: Type of this memory
            user_id: Optional user ID for user-specific memories
        """
        self._memory_type = memory_type
        self._user_id = user_id

    @property
    def memory_type(self) -> MemoryType:
        """Get the memory type."""
        return self._memory_type

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID."""
        return self._user_id

    @abstractmethod
    def save(self, entry: MemoryEntry) -> bool:
        """
        Save a memory entry.

        Args:
            entry: Memory entry to save

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            MemoryEntry if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search for memory entries.

        Args:
            query: Search query string
            filters: Additional filters (e.g., {'importance': 5})
            limit: Maximum number of results

        Returns:
            List of matching MemoryEntry objects
        """
        pass

    @abstractmethod
    def update(self, memory_id: str, **kwargs) -> Optional[MemoryEntry]:
        """
        Update a memory entry.

        Args:
            memory_id: ID of the memory to update
            **kwargs: Fields to update

        Returns:
            Updated MemoryEntry if successful, None otherwise
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all memories of this type.

        Returns:
            True if cleared successfully, False otherwise
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Get the count of memory entries.

        Returns:
            Number of entries
        """
        pass

    @abstractmethod
    def cleanup(self) -> int:
        """
        Perform cleanup (e.g., remove expired entries).

        Returns:
            Number of entries removed
        """
        pass

    def _create_entry(
        self,
        content: str,
        importance: int = 3,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> MemoryEntry:
        """
        Helper to create a MemoryEntry with default values.

        Args:
            content: Memory content
            importance: Importance score (1-5)
            metadata: Optional metadata
            tags: Optional tags
            session_id: Optional session ID

        Returns:
            New MemoryEntry instance
        """
        return MemoryEntry(
            content=content,
            memory_type=self._memory_type,
            importance=importance,
            user_id=self._user_id,
            metadata=metadata or {},
            tags=tags or [],
            session_id=session_id,
        )