"""
Memory Configuration

Configuration settings for the memory system loaded from core config.
Centralizes all memory-related configuration values.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Import MemoryType and MemoryImportance from models as the single source of truth
from .models import MemoryType, MemoryImportance


class MemoryBackendType(str, Enum):
    """Supported memory storage backend types."""

    JSON = "json"
    SQLITE = "sqlite"
    VECTOR = "vector"
    IN_MEMORY = "in_memory"


@dataclass
class MemoryConfig:
    """
    Configuration for the memory system.

    Attributes:
        backend_type: Storage backend to use (json, sqlite, vector, in_memory)
        storage_path: Path to storage file/directory
        max_entries_per_type: Maximum entries allowed per memory type
        ttl_seconds: Time-to-live for short-term memories (None = no expiry)
        retention_days: Days to retain long-term memories (None = forever)
        enable_deduplication: Whether to check for duplicates before saving
        deduplication_threshold: Similarity threshold for duplicate detection (0-1)
        importance_threshold: Minimum importance score to save as long-term memory
        auto_save_conversation: Automatically save conversation history
        conversation_max_turns: Maximum conversation turns to keep in memory
        user_preferences_enabled: Whether to store user preferences
        vector_store_enabled: Whether to enable vector search (requires vector backend)
        embedding_model: Model name for generating embeddings (if vector search enabled)
    """

    backend_type: MemoryBackendType = MemoryBackendType.JSON
    storage_path: str = "data/memory.json"
    max_entries_per_type: dict[MemoryType, int] = field(
        default_factory=lambda: {
            MemoryType.USER: 100,
            MemoryType.CONVERSATION: 50,
            MemoryType.SHORT_TERM: 200,
            MemoryType.LONG_TERM: 1000,
            MemoryType.PROJECT: 50,
            MemoryType.TASK: 100,
            MemoryType.PREFERENCE: 50,
        }
    )
    ttl_seconds: Optional[int] = 3600  # 1 hour for short-term
    retention_days: Optional[int] = 90  # 90 days for long-term
    enable_deduplication: bool = True
    deduplication_threshold: float = 0.85
    importance_threshold: int = 4  # 1-5 scale, only save high-importance as long-term
    auto_save_conversation: bool = True
    conversation_max_turns: int = 20
    user_preferences_enabled: bool = True
    vector_store_enabled: bool = False
    embedding_model: str = "text-embedding-3-small"

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create MemoryConfig from environment variables / core config."""
        from core.config import get_config

        try:
            config = get_config()
            memory_section = config.memory

            backend_str = memory_section.get("backend_type", "json")
            try:
                backend_type = MemoryBackendType(backend_str.lower())
            except ValueError:
                backend_type = MemoryBackendType.JSON

            return cls(
                backend_type=backend_type,
                storage_path=memory_section.get("storage_path", "data/memory.json"),
                ttl_seconds=memory_section.get("ttl_seconds", 3600),
                retention_days=memory_section.get("retention_days", 90),
                enable_deduplication=memory_section.get("enable_deduplication", True),
                deduplication_threshold=memory_section.get(
                    "deduplication_threshold", 0.85
                ),
                importance_threshold=memory_section.get("importance_threshold", 4),
                auto_save_conversation=memory_section.get(
                    "auto_save_conversation", True
                ),
                conversation_max_turns=memory_section.get("conversation_max_turns", 20),
                user_preferences_enabled=memory_section.get(
                    "user_preferences_enabled", True
                ),
                vector_store_enabled=memory_section.get("vector_store_enabled", False),
                embedding_model=memory_section.get(
                    "embedding_model", "text-embedding-3-small"
                ),
            )
        except Exception:
            # Return defaults if config not available
            return cls()


# Global config instance
_memory_config: Optional[MemoryConfig] = None


def get_memory_config() -> MemoryConfig:
    """Get the global memory configuration."""
    global _memory_config
    if _memory_config is None:
        _memory_config = MemoryConfig.from_env()
    return _memory_config


def reset_memory_config() -> None:
    """Reset the global config (useful for testing)."""
    global _memory_config
    _memory_config = None