"""
IRON BOLT - Memory System
Enables AI to remember conversations, user preferences, and project context.
Architecture: Memory Manager coordinates different memory types.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os


class MemoryEntry:
    """Single memory entry."""

    def __init__(self, content: str, memory_type: str = "conversation", 
                 metadata: Dict = None, importance: int = 1):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.content = content
        self.memory_type = memory_type  # user, conversation, project, task
        self.metadata = metadata or {}
        self.importance = importance  # 1-5 scale
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.memory_type,
            "metadata": self.metadata,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        entry = cls.__new__(cls)
        entry.id = data["id"]
        entry.content = data["content"]
        entry.memory_type = data["type"]
        entry.metadata = data.get("metadata", {})
        entry.importance = data.get("importance", 1)
        entry.created_at = data["created_at"]
        entry.updated_at = data.get("updated_at", entry.created_at)
        return entry


class BaseMemoryStore:
    """Base class for memory storage backends."""

    def save(self, entry: MemoryEntry):
        raise NotImplementedError

    def search(self, query: str, memory_type: Optional[str] = None, limit: int = 5) -> List[MemoryEntry]:
        raise NotImplementedError

    def get_all(self, memory_type: Optional[str] = None) -> List[MemoryEntry]:
        raise NotImplementedError

    def delete(self, memory_id: str):
        raise NotImplementedError

    def update(self, memory_id: str, content: str):
        raise NotImplementedError


class JSONMemoryStore(BaseMemoryStore):
    """JSON file-based memory store for AR1."""

    def __init__(self, storage_path: str = "data/memory.json"):
        self.storage_path = storage_path
        self.memories: List[MemoryEntry] = []
        self._load()

    def _load(self):
        """Load memories from file."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [MemoryEntry.from_dict(m) for m in data]
            except Exception as e:
                print(f"[Memory Warning] Could not load memory: {e}")
                self.memories = []

    def _save(self):
        """Save memories to file."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in self.memories], f, indent=2, ensure_ascii=False)

    def save(self, entry: MemoryEntry):
        """Save a memory entry."""
        # Check for duplicates
        for existing in self.memories:
            if existing.content == entry.content and existing.memory_type == entry.memory_type:
                existing.updated_at = datetime.now().isoformat()
                self._save()
                return

        self.memories.append(entry)
        self._save()

    def search(self, query: str, memory_type: Optional[str] = None, limit: int = 5) -> List[MemoryEntry]:
        """Simple keyword-based search for AR1."""
        query_lower = query.lower()
        results = []

        for memory in reversed(self.memories):  # Most recent first
            if memory_type and memory.memory_type != memory_type:
                continue

            if query_lower in memory.content.lower():
                results.append(memory)
                if len(results) >= limit:
                    break

        return results

    def get_all(self, memory_type: Optional[str] = None) -> List[MemoryEntry]:
        """Get all memories, optionally filtered by type."""
        if memory_type:
            return [m for m in self.memories if m.memory_type == memory_type]
        return self.memories.copy()

    def delete(self, memory_id: str):
        """Delete a memory by ID."""
        self.memories = [m for m in self.memories if m.id != memory_id]
        self._save()

    def update(self, memory_id: str, content: str):
        """Update a memory's content."""
        for memory in self.memories:
            if memory.id == memory_id:
                memory.content = content
                memory.updated_at = datetime.now().isoformat()
                self._save()
                return


class MemoryManager:
    """
    Central controller for memory operations.
    Single Responsibility: Manage all memory types and storage.
    """

    def __init__(self, storage_path: str = "data/memory.json"):
        self.store = JSONMemoryStore(storage_path)
        self.conversation_history: List[Dict] = []

    def save(self, content: str, memory_type: str = "conversation", 
             metadata: Dict = None, importance: int = 1):
        """Save a memory entry."""
        entry = MemoryEntry(content, memory_type, metadata, importance)
        self.store.save(entry)
        print(f"[Memory] Saved: {memory_type} - {content[:50]}...")

    def save_conversation(self, user_message: str, assistant_response: str):
        """Save a conversation turn."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat()
        })

        # Also save to long-term memory
        content = f"User: {user_message}\nAssistant: {assistant_response}"
        self.save(content, memory_type="conversation", importance=1)

    def search(self, query: str, memory_type: Optional[str] = None, limit: int = 5) -> List[str]:
        """Search memories and return content strings."""
        results = self.store.search(query, memory_type, limit)
        return [r.content for r in results]

    def get_user_memory(self) -> Dict[str, Any]:
        """Get user-specific memories."""
        memories = self.store.get_all("user")
        return {m.metadata.get("key", "unknown"): m.content for m in memories}

    def save_user_preference(self, key: str, value: str):
        """Save a user preference."""
        self.save(value, memory_type="user", metadata={"key": key}, importance=3)

    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        return self.conversation_history[-limit:]

    def clear_conversation(self):
        """Clear current conversation history."""
        self.conversation_history = []

    def delete_memory(self, memory_id: str):
        """Delete a memory by ID."""
        self.store.delete(memory_id)


# Singleton instance
_memory_manager_instance = None

def get_memory_manager(storage_path: str = "data/memory.json") -> MemoryManager:
    """Get or create global memory manager."""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager(storage_path)
    return _memory_manager_instance
