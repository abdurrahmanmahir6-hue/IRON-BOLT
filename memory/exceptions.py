"""
Memory Layer Exceptions

Custom exceptions for memory operations to provide clear error handling
and debugging information.
"""

from typing import Optional, Any


class MemoryError(Exception):
    """Base exception for all memory-related errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class MemoryStorageError(MemoryError):
    """Raised when storage backend operations fail."""

    pass


class MemoryRetrievalError(MemoryError):
    """Raised when memory retrieval operations fail."""

    pass


class MemoryUpdateError(MemoryError):
    """Raised when memory update operations fail."""

    pass


class MemoryNotFoundError(MemoryError):
    """Raised when requested memory entry is not found."""

    pass


class MemoryValidationError(MemoryError):
    """Raised when memory data validation fails."""

    pass


class MemoryConfigurationError(MemoryError):
    """Raised when memory configuration is invalid."""

    pass


class MemoryDuplicateError(MemoryError):
    """Raised when attempting to save a duplicate memory entry."""

    pass


class MemoryCapacityExceededError(MemoryError):
    """Raised when memory storage capacity limits are exceeded."""

    pass