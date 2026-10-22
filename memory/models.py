"""
Memory Data Models

Canonical data structures for memory entries used throughout the memory system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any
from enum import Enum
import uuid


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def as_utc_datetime(value: Any) -> Optional[datetime]:
    """Normalize legacy strings, naive datetimes, and aware datetimes to UTC."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    elif not isinstance(value, datetime):
        raise TypeError(f"Expected datetime or ISO string, got {type(value).__name__}")

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class MemoryType(str, Enum):
    """Types of memory entries."""

    USER = "user"
    CONVERSATION = "conversation"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    PROJECT = "project"
    TASK = "task"
    PREFERENCE = "preference"


class MemoryImportance(int, Enum):
    """Importance levels for memory entries (1-5 scale)."""

    TRIVIAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class MemoryEntry:
    """
    Represents a single memory entry in the system.

    Attributes:
        id: Unique identifier for this memory entry
        content: The actual memory content/text
        memory_type: Type of memory (user, conversation, short_term, etc.)
        importance: Importance score (1-5)
        user_id: ID of the user this memory belongs to (for multi-user support)
        session_id: Session ID for conversation-bound memories
        metadata: Additional structured data about this memory
        created_at: Timestamp when memory was created
        updated_at: Timestamp when memory was last updated
        expires_at: Optional expiry timestamp (for TTL-based cleanup)
        access_count: Number of times this memory has been accessed
        last_accessed: Timestamp of last access
        tags: List of tags for categorization and search
        source: Where this memory originated (e.g., 'conversation', 'tool', 'user_input')
        embedding: Optional vector embedding for semantic search
    """

    content: str
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: MemoryImportance = MemoryImportance.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    source: str = "unknown"
    embedding: Optional[list[float]] = None

    def __post_init__(self):
        """Validate and normalize the memory entry after initialization."""
        self.created_at = as_utc_datetime(self.created_at) or utc_now()
        self.updated_at = as_utc_datetime(self.updated_at) or self.created_at
        self.expires_at = as_utc_datetime(self.expires_at)
        self.last_accessed = as_utc_datetime(self.last_accessed)

        # Convert string memory_type to enum if needed
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)

        # Convert int importance to enum if needed
        if isinstance(self.importance, int):
            # Validate importance range
            if not (1 <= self.importance <= 5):
                from .exceptions import MemoryValidationError
                raise MemoryValidationError(
                    f"Importance must be between 1 and 5, got {self.importance}"
                )
            self.importance = MemoryImportance(self.importance)

        # Ensure metadata is a dict
        if self.metadata is None:
            self.metadata = {}

        # Ensure tags is a list
        if self.tags is None:
            self.tags = []

    def is_expired(self) -> bool:
        """Check if this memory entry has expired."""
        if self.expires_at is None:
            return False
        return utc_now() > self.expires_at

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = utc_now()

    def update_content(self, new_content: str) -> None:
        """Update the content and refresh the updated_at timestamp."""
        self.content = new_content
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": (
                self.last_accessed.isoformat() if self.last_accessed else None
            ),
            "tags": self.tags,
            "source": self.source,
            # Note: embedding is not serialized by default for security/size reasons
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """
        Create MemoryEntry from dictionary.

        Does NOT mutate the input dictionary - makes a shallow copy first.
        """
        # Make a shallow copy to avoid mutating caller's data
        data_copy = data.copy()

        # Parse datetime fields without double-parsing already parsed values.
        for date_field in ["created_at", "updated_at", "expires_at", "last_accessed"]:
            if data_copy.get(date_field) is not None:
                try:
                    data_copy[date_field] = as_utc_datetime(data_copy[date_field])
                except (ValueError, TypeError):
                    data_copy[date_field] = None

        # Handle None for optional fields
        if data_copy.get("expires_at") is None:
            data_copy["expires_at"] = None
        if data_copy.get("last_accessed") is None:
            data_copy["last_accessed"] = None

        return cls(**data_copy)

    def __eq__(self, other: object) -> bool:
        """Check equality based on content and type."""
        if not isinstance(other, MemoryEntry):
            return False
        return (
            self.content == other.content
            and self.memory_type == other.memory_type
            and self.user_id == other.user_id
        )

    def __hash__(self) -> int:
        """Generate hash based on content, type, and user_id."""
        return hash((self.content, self.memory_type, self.user_id))

    def similarity_score(self, other: "MemoryEntry") -> float:
        """
        Calculate similarity score between two memory entries.
        Returns a value between 0.0 (completely different) and 1.0 (identical).

        Uses simple string similarity for now; can be enhanced with embeddings.
        """
        if self.embedding and other.embedding:
            # Cosine similarity for vector embeddings
            dot_product = sum(a * b for a, b in zip(self.embedding, other.embedding))
            norm_self = sum(a * a for a in self.embedding) ** 0.5
            norm_other = sum(b * b for b in other.embedding) ** 0.5
            if norm_self > 0 and norm_other > 0:
                return dot_product / (norm_self * norm_other)

        # Fallback to simple string similarity
        s1 = self.content.lower()
        s2 = other.content.lower()
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        # Simple Jaccard similarity
        words1 = set(s1.split())
        words2 = set(s2.split())
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0


@dataclass
class ConversationTurn:
    """
    Represents a single turn in a conversation (user message + AI response).

    Attributes:
        user_message: The user's input
        ai_response: The AI's response
        timestamp: When this turn occurred
        context: Optional context/metadata about this turn
    """

    user_message: str
    ai_response: str
    timestamp: datetime = field(default_factory=utc_now)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationTurn":
        """Create ConversationTurn from dictionary."""
        data_copy = data.copy()
        if data_copy.get("timestamp") is not None:
            data_copy["timestamp"] = as_utc_datetime(data_copy["timestamp"])
        return cls(**data_copy)


@dataclass
class UserPreferences:
    """
    Stores user preferences in memory.

    Attributes:
        user_id: Unique user identifier
        language: Preferred language
        timezone: User's timezone
        communication_style: Preferred communication style (formal, casual, etc.)
        topics_of_interest: Topics the user is interested in
        custom_preferences: Additional custom preferences
    """

    user_id: str
    language: str = "en"
    timezone: str = "UTC"
    communication_style: str = "casual"
    topics_of_interest: list[str] = field(default_factory=list)
    custom_preferences: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "language": self.language,
            "timezone": self.timezone,
            "communication_style": self.communication_style,
            "topics_of_interest": self.topics_of_interest,
            "custom_preferences": self.custom_preferences,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        """Create UserPreferences from dictionary."""
        data_copy = data.copy()
        if data_copy.get("updated_at") is not None:
            data_copy["updated_at"] = as_utc_datetime(data_copy["updated_at"])
        return cls(**data_copy)

    def update_preference(self, key: str, value: Any) -> None:
        """Update a specific preference."""
        if key in ["language", "timezone", "communication_style"]:
            setattr(self, key, value)
        elif key == "topics_of_interest":
            self.topics_of_interest = value if isinstance(value, list) else [value]
        else:
            self.custom_preferences[key] = value
        self.updated_at = utc_now()
