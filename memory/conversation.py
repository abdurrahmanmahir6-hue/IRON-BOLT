"""
Conversation Memory Implementation

Manages conversation history and context for multi-turn conversations.
Stores user messages, AI responses, and conversation metadata.
"""

from typing import Optional, Any, List
from datetime import datetime

from .base_memory import BaseMemory
from .models import MemoryEntry, MemoryType, ConversationTurn
from .storage import BaseStorageBackend
from .config import MemoryConfig, get_memory_config


class ConversationMemory(BaseMemory):
    """
    Conversation memory implementation.

    Manages:
    - Conversation turns (user message + AI response pairs)
    - Conversation context and metadata
    - Session-based conversation tracking
    """

    def __init__(
        self,
        storage: BaseStorageBackend,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
    ):
        """
        Initialize conversation memory.

        Args:
            storage: Storage backend instance
            user_id: User ID for this conversation
            session_id: Session ID for this conversation
            config: Memory configuration
        """
        super().__init__(MemoryType.CONVERSATION, user_id)
        self._storage = storage
        self._session_id = session_id
        self._config = config or get_memory_config()
        self._max_turns = self._config.conversation_max_turns

    def add_turn(
        self,
        user_message: str,
        ai_response: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Optional[MemoryEntry]:
        """
        Add a conversation turn.

        Args:
            user_message: User's input message
            ai_response: AI's response
            context: Optional context/metadata

        Returns:
            Created MemoryEntry or None if failed
        """
        turn = ConversationTurn(
            user_message=user_message,
            ai_response=ai_response,
            context=context or {},
        )

        # Create memory entry with turn data
        content = f"User: {user_message}\n\nAssistant: {ai_response}"
        entry = MemoryEntry(
            content=content,
            memory_type=self._memory_type,
            user_id=self._user_id,
            session_id=self._session_id,
            metadata={"turn": turn.to_dict()},
            tags=["conversation"],
            source="conversation",
        )

        if self.save(entry):
            return entry
        return None

    def get_turns(
        self,
        limit: int = 10,
        include_metadata: bool = True,
    ) -> list[ConversationTurn]:
        """
        Get recent conversation turns.

        Args:
            limit: Maximum number of turns to return
            include_metadata: Whether to include metadata

        Returns:
            List of ConversationTurn objects
        """
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )

        # Filter by session if set
        if self._session_id:
            entries = [e for e in entries if e.session_id == self._session_id]

        # Filter out expired
        entries = [e for e in entries if not e.is_expired()]

        # Sort by recency
        entries.sort(key=lambda e: e.created_at, reverse=True)

        # Extract turns from metadata
        turns = []
        for entry in entries[:limit]:
            if "turn" in entry.metadata:
                turn_data = entry.metadata["turn"]
                turn = ConversationTurn.from_dict(turn_data)
                turns.append(turn)

        # Return in chronological order
        turns.reverse()
        return turns

    def get_context_string(self, max_turns: Optional[int] = None) -> str:
        """
        Get conversation context as a formatted string.

        Args:
            max_turns: Maximum turns to include (uses default if None)

        Returns:
            Formatted conversation history string
        """
        if max_turns is None:
            max_turns = self._max_turns

        turns = self.get_turns(limit=max_turns)
        if not turns:
            return ""

        context_lines = []
        for turn in turns:
            context_lines.append(f"User: {turn.user_message}")
            context_lines.append(f"Assistant: {turn.ai_response}")

        return "\n".join(context_lines)

    def save(self, entry: MemoryEntry) -> bool:
        """Save a conversation memory entry."""
        if entry.memory_type != self._memory_type:
            entry.memory_type = self._memory_type
        if self._user_id and not entry.user_id:
            entry.user_id = self._user_id
        if self._session_id and not entry.session_id:
            entry.session_id = self._session_id
        return self._storage.save(entry)

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        return self._storage.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self._storage.delete(memory_id)

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search for conversation memories."""
        if filters is None:
            filters = {}
        filters["memory_type"] = self._memory_type
        if self._user_id:
            filters["user_id"] = self._user_id
        if self._session_id:
            filters["session_id"] = self._session_id
        return self._storage.search(query=query, filters=filters, limit=limit)

    def update(self, memory_id: str, **kwargs) -> Optional[MemoryEntry]:
        """Update a memory entry."""
        entry = self._storage.get(memory_id)
        if not entry:
            return None
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = datetime.utcnow()
        if self._storage.update(entry):
            return entry
        return None

    def clear(self) -> bool:
        """Clear all conversation memories for this session/user."""
        # Clear only for current session/user combination
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )
        for entry in entries:
            if self._session_id is None or entry.session_id == self._session_id:
                self._storage.delete(entry.id)
        return True

    def count(self) -> int:
        """Get count of conversation memories."""
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )
        if self._session_id:
            entries = [e for e in entries if e.session_id == self._session_id]
        return len(entries)

    def cleanup(self) -> int:
        """Remove old conversations exceeding max_turns limit."""
        entries = self._storage.get_all(
            memory_type=self._memory_type,
            user_id=self._user_id,
        )
        if self._session_id:
            entries = [e for e in entries if e.session_id == self._session_id]

        # Sort by recency
        entries.sort(key=lambda e: e.created_at, reverse=True)

        # Delete excess entries
        removed = 0
        if len(entries) > self._max_turns:
            for entry in entries[self._max_turns:]:
                if self._storage.delete(entry.id):
                    removed += 1

        return removed

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current conversation session.

        Returns:
            Dictionary with session statistics
        """
        turns = self.get_turns(limit=self._max_turns)
        return {
            "user_id": self._user_id,
            "session_id": self._session_id,
            "turn_count": len(turns),
            "first_turn": turns[0].timestamp.isoformat() if turns else None,
            "last_turn": turns[-1].timestamp.isoformat() if turns else None,
        }