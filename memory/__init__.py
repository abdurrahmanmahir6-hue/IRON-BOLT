"""
Memory Layer - Core Module

This module provides the central interface for all memory operations in IRON-BOLT.
All tools and agents access memory only through MemoryManager.

Architecture:
- MemoryManager: Central controller coordinating all memory operations
- Delegates to specialized modules: storage, retrieval, update, decision
- Supports multiple memory types: user, conversation, short-term, long-term
- Pluggable storage backends (JSON, SQLite, Vector, etc.)
"""

from .manager import MemoryManager, get_memory_manager

__all__ = [
    "MemoryManager",
    "get_memory_manager",
]