"""
Memory Update System

Handles updating, modifying, and maintaining memory entries.
Provides strategies for intelligent memory updates.
"""

from typing import Optional, Any, List
from datetime import datetime

from .models import MemoryEntry, MemoryType, utc_now
from .storage import BaseStorageBackend
from .exceptions import MemoryUpdateError, MemoryNotFoundError
from .utils import calculate_similarity


class MemoryUpdater:
    """
    Handles memory update operations.

    Provides methods for:
    - Updating memory content
    - Merging duplicate memories
    - Refreshing timestamps
    - Batch updates
    """

    def __init__(self, storage: BaseStorageBackend):
        """
        Initialize updater.

        Args:
            storage: Storage backend to update
        """
        self._storage = storage

    def update_entry(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        merge: bool = False,
    ) -> Optional[MemoryEntry]:
        """
        Update a memory entry.

        Args:
            memory_id: ID of the memory to update
            content: New content (optional)
            importance: New importance score (optional)
            metadata: Metadata to merge/add (optional)
            tags: New tags list (replaces existing if provided)
            merge: If True, append content instead of replacing

        Returns:
            Updated MemoryEntry if successful, None otherwise

        Raises:
            MemoryNotFoundError: If memory_id doesn't exist
            MemoryUpdateError: If update fails
        """
        try:
            entry = self._storage.get(memory_id)
            if not entry:
                raise MemoryNotFoundError(f"Memory {memory_id} not found")

            # Update fields
            if content:
                if merge:
                    entry.content = entry.content + "\n\n" + content
                else:
                    entry.content = content

            if importance is not None:
                entry.importance = importance

            if metadata:
                entry.metadata.update(metadata)

            if tags is not None:
                entry.tags = tags

            entry.updated_at = utc_now()

            if self._storage.update(entry):
                return entry
            else:
                raise MemoryUpdateError(f"Failed to persist update for {memory_id}")

        except MemoryNotFoundError:
            raise
        except Exception as e:
            if isinstance(e, MemoryNotFoundError):
                raise
            raise MemoryUpdateError(f"Update failed: {e}")

    def merge_similar_memories(
        self,
        memory_id1: str,
        memory_id2: str,
        keep_higher_importance: bool = True,
    ) -> Optional[MemoryEntry]:
        """
        Merge two similar memories into one.

        Args:
            memory_id1: First memory ID
            memory_id2: Second memory ID
            keep_higher_importance: Keep the one with higher importance as base

        Returns:
            Merged MemoryEntry, or None if merge fails
        """
        try:
            entry1 = self._storage.get(memory_id1)
            entry2 = self._storage.get(memory_id2)

            if not entry1 or not entry2:
                raise MemoryNotFoundError("One or both memories not found")

            # Determine which to keep as base
            if keep_higher_importance:
                base = entry1 if entry1.importance.value >= entry2.importance.value else entry2
                other = entry2 if base == entry1 else entry1
            else:
                base = entry1
                other = entry2

            # Merge content
            base.content = base.content + "\n\n[Additional info]: " + other.content

            # Merge tags (unique)
            all_tags = set(base.tags) | set(other.tags)
            base.tags = list(all_tags)

            # Merge metadata
            base.metadata.update(other.metadata)

            # Update timestamp
            base.updated_at = utc_now()

            # Save merged entry
            if not self._storage.update(base):
                raise MemoryUpdateError("Failed to save merged memory")

            # Delete the other entry
            self._storage.delete(other.id)

            return base

        except MemoryNotFoundError:
            raise
        except Exception as e:
            if isinstance(e, MemoryNotFoundError):
                raise
            raise MemoryUpdateError(f"Merge failed: {e}")

    def refresh_timestamp(self, memory_id: str) -> bool:
        """
        Refresh the updated_at timestamp of a memory.

        Args:
            memory_id: ID of the memory to refresh

        Returns:
            True if successful, False otherwise
        """
        try:
            entry = self._storage.get(memory_id)
            if not entry:
                return False

            entry.updated_at = utc_now()
            return self._storage.update(entry)
        except Exception:
            return False

    def batch_update(
        self,
        updates: list[tuple[str, dict[str, Any]]],
    ) -> tuple[int, int]:
        """
        Perform batch updates on multiple memories.

        Args:
            updates: List of (memory_id, update_fields) tuples

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        for memory_id, fields in updates:
            try:
                self.update_entry(memory_id, **fields)
                successful += 1
            except Exception:
                failed += 1

        return successful, failed

    def increment_access_count(self, memory_id: str) -> bool:
        """
        Increment the access count for a memory.

        Args:
            memory_id: ID of the memory

        Returns:
            True if successful, False otherwise
        """
        try:
            entry = self._storage.get(memory_id)
            if not entry:
                return False

            entry.touch()  # Increments access_count and updates last_accessed
            return self._storage.update(entry)
        except Exception:
            return False
