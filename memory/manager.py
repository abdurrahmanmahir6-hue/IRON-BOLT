"""
Memory Manager - Central Controller

Main entry point for all memory operations. Coordinates between storage,
retrieval, update, and decision components to provide a unified interface.
"""

from typing import Optional, Any, List
from datetime import datetime

from .models import MemoryEntry, MemoryType, MemoryImportance, utc_now
from .config import MemoryConfig, get_memory_config
from .storage import BaseStorageBackend, create_storage_backend, JSONStorage
from .retrieval import MemoryRetriever
from .update import MemoryUpdater
from .decision import MemoryDecisionMaker
from .short_term import ShortTermMemory
from .conversation import ConversationMemory
from .exceptions import MemoryError, MemoryConfigurationError


class MemoryManager:
    """
    Central controller for all memory operations.

    Provides unified interface for:
    - Saving and retrieving memories
    - Managing different memory types
    - Automatic cleanup and maintenance
    - Context retrieval for conversations
    """

    _instance: Optional["MemoryManager"] = None

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        storage: Optional[BaseStorageBackend] = None,
    ):
        """
        Initialize the Memory Manager.

        Args:
            config: Memory configuration (uses default if not provided)
            storage: Storage backend (creates default if not provided)
        """
        self._config = config or get_memory_config()
        self._storage = storage or create_storage_backend(
            self._config.backend_type.value,
            {
                "storage_path": self._config.storage_path,
            },
        )

        # Initialize storage
        self._storage.initialize()

        # Initialize components
        self._retriever = MemoryRetriever(self._storage)
        self._updater = MemoryUpdater(self._storage)
        self._decision_maker = MemoryDecisionMaker(self._storage, self._config)

        # Initialize specialized memory handlers
        self._short_term = ShortTermMemory(self._storage, config=self._config)
        self._conversation: Optional[ConversationMemory] = None

    @classmethod
    def get_instance(cls) -> "MemoryManager":
        """Get singleton instance of MemoryManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None

    # === Core Memory Operations ===

    def save(self, content: str, memory_type: MemoryType = MemoryType.SHORT_TERM, importance: Optional[int] = None, metadata: Optional[dict[str, Any]] = None, tags: Optional[list[str]] = None, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Optional[MemoryEntry]:
        """
        Save a new memory entry.

        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score (1-5), or None to auto-determine
            metadata: Optional metadata
            tags: Optional tags
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            Created MemoryEntry or None if failed
        """
        # Check if should save
        should_save, reason = self._decision_maker.should_save(
            content,
            {"memory_type": memory_type, "session_id": session_id},
            user_id=user_id,
        )
        if not should_save:
            return None

        # Determine importance: None means auto-determine
        if importance is None:
            importance = self._decision_maker.determine_importance(content).value

        # Validate importance range
        if not (1 <= importance <= 5):
            raise ValueError(f"Importance must be between 1 and 5, got {importance}")

        # Create entry
        from .models import MemoryImportance
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=MemoryImportance(importance),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )

        # Set expiry for short-term memories
        if memory_type == MemoryType.SHORT_TERM and self._config.ttl_seconds:
            from .utils import generate_expiry_timestamp
            entry.expires_at = generate_expiry_timestamp(self._config.ttl_seconds)

        if self._storage.save(entry):
            return entry
        return None

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        return self._retriever.get_by_id(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self._storage.delete(memory_id)

    def search(
        self,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search for memories."""
        return self._retriever.search(
            query=query,
            memory_type=memory_type,
            user_id=user_id,
            limit=limit,
        )

    def update(self, memory_id: str, **kwargs) -> Optional[MemoryEntry]:
        """Update a memory entry."""
        return self._updater.update_entry(memory_id, **kwargs)

    # === Specialized Memory Access ===

    def short_term(self, user_id: Optional[str] = None) -> ShortTermMemory:
        """Get short-term memory handler."""
        return ShortTermMemory(self._storage, user_id=user_id, config=self._config)

    def conversation(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ConversationMemory:
        """Get conversation memory handler."""
        return ConversationMemory(
            self._storage,
            user_id=user_id,
            session_id=session_id,
            config=self._config,
        )

    def save_conversation(
        self,
        user_message: str,
        ai_response: str,
        user_id: str = "default_user",
        session_id: Optional[str] = "default_session",
        timestamp=None,
    ) -> Optional[MemoryEntry]:
        """Save a conversation turn."""
        conv = self.conversation(user_id=user_id, session_id=session_id)
        return conv.add_turn(
            user_message=user_message,
            ai_response=ai_response,
            timestamp=timestamp or utc_now(),
        )

    def get_conversation_history(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = "default_session",
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """Get recent conversation history as a list of message dicts."""
        conv = self.conversation(user_id=user_id, session_id=session_id)
        turns = conv.get_turns(limit=limit)
        history: list[dict[str, str]] = []
        for turn in turns:
            history.append({"role": "user", "content": turn.user_message})
            history.append({"role": "assistant", "content": turn.ai_response})
        return history

    # === Context Retrieval ===

    def get_context_for_conversation(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        max_memories: int = 5,
    ) -> list[MemoryEntry]:
        """Get relevant context for a conversation."""
        return self._retriever.get_context_for_conversation(
            user_id=user_id,
            session_id=session_id,
            max_memories=max_memories,
        )

    def get_recent(
        self,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Get recent memories."""
        return self._retriever.get_recent(
            memory_type=memory_type,
            user_id=user_id,
            limit=limit,
        )

    # === Maintenance ===

    def cleanup(self, dry_run: bool = False) -> dict[str, int]:
        """Perform memory cleanup."""
        # Cleanup expired entries
        stats = self._decision_maker.cleanup(dry_run=dry_run)

        # Cleanup individual memory types
        stats["short_term_cleaned"] = self._short_term.cleanup()

        if self._conversation:
            stats["conversation_cleaned"] = self._conversation.cleanup()

        return stats

    def count_by_type(self, user_id: Optional[str] = None) -> dict[MemoryType, int]:
        """Get counts of memories by type."""
        return self._retriever.count_by_type(user_id=user_id)

    def get_stats(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """Get memory system statistics."""
        counts = self.count_by_type(user_id)
        total = sum(counts.values())

        return {
            "total_memories": total,
            "by_type": {t.value: c for t, c in counts.items()},
            "storage_type": self._config.backend_type.value,
            "ttl_seconds": self._config.ttl_seconds,
            "retention_days": self._config.retention_days,
        }

    def close(self) -> bool:
        """Close the memory manager and release resources."""
        if self._storage:
            self._storage.close()
        return True


# Convenience function for getting memory manager instance
def get_memory_manager() -> MemoryManager:
    """Get the singleton MemoryManager instance."""
    return MemoryManager.get_instance()
