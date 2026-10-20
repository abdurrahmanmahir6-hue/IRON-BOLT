"""
Memory Retrieval System

Handles searching, filtering, and retrieving memories from storage.
Provides both simple and advanced retrieval strategies.
"""

from typing import Optional, Any, List
from datetime import datetime

from .models import MemoryEntry, MemoryType, MemoryImportance
from .storage import BaseStorageBackend
from .exceptions import MemoryRetrievalError
from .utils import calculate_similarity, normalize_text


class MemoryRetriever:
    """
    Handles memory retrieval operations.

    Provides methods for:
    - Simple search by query
    - Filtered search by metadata
    - Semantic search (future)
    - Context-aware retrieval
    - Recency-based retrieval
    """

    def __init__(self, storage: BaseStorageBackend):
        """
        Initialize retriever.

        Args:
            storage: Storage backend to retrieve from
        """
        self._storage = storage

    def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a single memory by ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            MemoryEntry if found, None otherwise
        """
        try:
            entry = self._storage.get(memory_id)
            if entry and not entry.is_expired():
                entry.touch()
                return entry
            return None
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to retrieve memory {memory_id}: {e}")

    def search(
        self,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        min_importance: Optional[MemoryImportance] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MemoryEntry]:
        """
        Search for memories with various filters.

        Args:
            query: Text search query
            memory_type: Filter by memory type
            user_id: Filter by user ID
            min_importance: Minimum importance level (returns entries >= this level)
            tags: Filter by tags (must have all specified tags)
            session_id: Filter by session ID
            limit: Maximum results to return
            include_expired: Whether to include expired memories

        Returns:
            List of matching MemoryEntry objects
        """
        try:
            # Build filters - note: min_importance is handled in post-filtering
            # because storage filter only supports exact matches
            filters: dict[str, Any] = {}
            if user_id:
                filters["user_id"] = user_id
            if session_id:
                filters["session_id"] = session_id

            # Get results from storage
            results = self._storage.search(
                query=query,
                filters=filters if filters else None,
                limit=limit * 2 if query else limit,  # Get more for post-filtering
            )

            # Apply additional filters
            filtered_results = []
            for entry in results:
                # Skip expired unless explicitly included
                if not include_expired and entry.is_expired():
                    continue

                # Filter by memory type
                if memory_type and entry.memory_type != memory_type:
                    continue

                # Filter by tags
                if tags and not all(tag in entry.tags for tag in tags):
                    continue

                # Filter by minimum importance (>= threshold, not ==)
                if min_importance and entry.importance.value < min_importance.value:
                    continue

                filtered_results.append(entry)

            # Apply query-based ranking if query provided
            if query:
                query_normalized = normalize_text(query)
                filtered_results.sort(
                    key=lambda e: calculate_similarity(query_normalized, normalize_text(e.content)),
                    reverse=True,
                )

            return filtered_results[:limit]

        except Exception as e:
            raise MemoryRetrievalError(f"Search failed: {e}")

    def get_recent(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Get most recent memories.

        Args:
            memory_type: Optional filter by type
            user_id: Optional filter by user
            limit: Maximum number to return

        Returns:
            List of recent MemoryEntry objects
        """
        try:
            entries = self._storage.get_all(
                memory_type=memory_type,
                user_id=user_id,
            )
            # Filter out expired
            entries = [e for e in entries if not e.is_expired()]
            # Sort by created_at descending
            entries.sort(key=lambda e: e.created_at, reverse=True)
            return entries[:limit]
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to get recent memories: {e}")

    def get_by_importance(
        self,
        importance: MemoryImportance,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Get memories by importance level.

        Args:
            importance: Importance level to filter by
            memory_type: Optional filter by type
            user_id: Optional filter by user
            limit: Maximum number to return

        Returns:
            List of MemoryEntry objects with specified importance
        """
        try:
            entries = self._storage.get_all(
                memory_type=memory_type,
                user_id=user_id,
            )
            # Filter by importance and expiry
            entries = [
                e
                for e in entries
                if e.importance == importance and not e.is_expired()
            ]
            # Sort by recency
            entries.sort(key=lambda e: e.created_at, reverse=True)
            return entries[:limit]
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to get memories by importance: {e}")

    def get_context_for_conversation(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        max_memories: int = 5,
    ) -> list[MemoryEntry]:
        """
        Retrieve relevant context for a conversation.

        Combines:
        - Recent conversation memories (scoped to session_id if provided)
        - Important user memories
        - Relevant long-term memories

        Args:
            user_id: User ID
            session_id: Optional session ID for current conversation
            max_memories: Maximum total memories to return

        Returns:
            List of context MemoryEntry objects
        """
        context_memories: list[MemoryEntry] = []

        # Get recent conversation memories - MUST respect session_id
        if session_id:
            # Filter specifically by both user_id AND session_id
            conv_memories = self.search(
                memory_type=MemoryType.CONVERSATION,
                user_id=user_id,
                limit=max_memories // 2,
            )
            # Additional filter to ensure only this session's memories
            conv_memories = [m for m in conv_memories if m.session_id == session_id]
            context_memories.extend(conv_memories)

        # Get important user memories
        user_memories = self.get_by_importance(
            importance=MemoryImportance.HIGH,
            memory_type=MemoryType.USER,
            user_id=user_id,
            limit=max_memories // 3,
        )
        context_memories.extend(user_memories)

        # Get critical long-term memories
        long_term = self.get_by_importance(
            importance=MemoryImportance.CRITICAL,
            memory_type=MemoryType.LONG_TERM,
            user_id=user_id,
            limit=max_memories // 3,
        )
        context_memories.extend(long_term)

        # Remove duplicates and sort by importance then recency
        seen_ids = set()
        unique_memories = []
        for mem in context_memories:
            if mem.id not in seen_ids:
                seen_ids.add(mem.id)
                unique_memories.append(mem)

        unique_memories.sort(
            key=lambda e: (e.importance.value, e.created_at),
            reverse=True,
        )

        return unique_memories[:max_memories]

    def count_by_type(
        self,
        user_id: Optional[str] = None,
    ) -> dict[MemoryType, int]:
        """
        Get counts of memories by type.

        Args:
            user_id: Optional filter by user

        Returns:
            Dictionary mapping MemoryType to count
        """
        try:
            entries = self._storage.get_all(user_id=user_id)
            # Filter out expired
            entries = [e for e in entries if not e.is_expired()]

            counts: dict[MemoryType, int] = {}
            for entry in entries:
                counts[entry.memory_type] = counts.get(entry.memory_type, 0) + 1

            return counts
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to count memories: {e}")