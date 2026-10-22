"""
Memory Decision System

Handles decisions about what to remember, what to forget, and memory management.
Uses configurable rules and heuristics for memory lifecycle management.
"""

from typing import Optional, Any, List
from datetime import datetime, timedelta

from .models import MemoryEntry, MemoryType, MemoryImportance, utc_now
from .storage import BaseStorageBackend
from .config import MemoryConfig
from .utils import is_duplicate, calculate_similarity


class MemoryDecisionMaker:
    """
    Makes decisions about memory lifecycle.

    Responsibilities:
    - Decide if new information should be saved as memory
    - Determine importance level for new memories
    - Identify memories that should be forgotten/deleted
    - Detect and handle duplicate memories
    - Manage memory capacity limits
    """

    def __init__(self, storage: BaseStorageBackend, config: Optional[MemoryConfig] = None):
        """
        Initialize decision maker.

        Args:
            storage: Storage backend
            config: Memory configuration
        """
        self._storage = storage
        self._config = config or MemoryConfig()

    def should_save(
        self,
        content: str,
        context: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Decide if content should be saved as memory.

        Args:
            content: Content to evaluate
            context: Optional context information
            user_id: User ID for scoping duplicate detection

        Returns:
            Tuple of (should_save, reason)
        """
        # Check for empty/meaningless content
        if not content or len(content.strip()) < 3:
            return False, "Content too short"

        # Check for duplicates (scoped to user)
        if self._config.enable_deduplication:
            # Create a temporary entry for duplicate checking
            temp_entry = MemoryEntry(
                content=content,
                memory_type=context.get("memory_type", MemoryType.SHORT_TERM) if context else MemoryType.SHORT_TERM,
                user_id=user_id,
                session_id=context.get("session_id") if context else None,
            )
            duplicates = self.find_duplicates(temp_entry, user_id=user_id)
            if duplicates:
                return False, f"Duplicate of existing memory {duplicates[0].id}"

        # Check capacity limits
        mem_type = context.get("memory_type", MemoryType.SHORT_TERM) if context else MemoryType.SHORT_TERM
        # Count only for this user if user_id provided
        current_count = self._storage.count(memory_type=mem_type)
        max_allowed = self._config.max_entries_per_type.get(mem_type, 100)

        if current_count >= max_allowed:
            return False, f"Memory type {mem_type.value} at capacity ({current_count}/{max_allowed})"

        return True, "Content qualifies for memory"

    def determine_importance(
        self,
        content: str,
        context: Optional[dict[str, Any]] = None,
    ) -> MemoryImportance:
        """
        Determine the importance level for a memory.

        Uses heuristics based on:
        - Content characteristics
        - Context information
        - User-specified importance

        Args:
            content: Memory content
            context: Optional context including user-specified importance

        Returns:
            Determined MemoryImportance level
        """
        # Check for explicit importance in context
        if context:
            if "importance" in context:
                imp = context["importance"]
                if isinstance(imp, int) and 1 <= imp <= 5:
                    return MemoryImportance(imp)
                elif isinstance(imp, MemoryImportance):
                    return imp

        # Analyze content for importance indicators
        content_lower = content.lower()

        # Critical keywords suggest high importance
        critical_indicators = [
            "important", "remember", "always", "never", "critical",
            "must", "essential", "key", "priority", "urgent"
        ]

        # Count indicator occurrences
        indicator_count = sum(1 for word in critical_indicators if word in content_lower)

        if indicator_count >= 2:
            return MemoryImportance.CRITICAL
        elif indicator_count == 1:
            return MemoryImportance.HIGH

        # Check for question marks (might be less important)
        if "?" in content:
            return MemoryImportance.MEDIUM

        # Default importance
        return MemoryImportance.MEDIUM

    def should_promote_to_long_term(self, entry: MemoryEntry) -> bool:
        """
        Decide if a short-term memory should be promoted to long-term.

        Current promotion criteria (simple and deterministic):
        - Importance meets or exceeds the configured threshold

        Note: This is a decision-only method. It does NOT perform the actual
        promotion. The caller is responsible for creating a new long-term
        memory entry if this returns True.

        Future enhancements could consider:
        - Access frequency (e.g., accessed more than N times)
        - Recency of updates
        - User feedback signals

        Args:
            entry: Memory entry to evaluate

        Returns:
            True if should be promoted, False otherwise
        """
        # Primary criterion: importance threshold
        if entry.importance.value >= self._config.importance_threshold:
            return True

        return False

    def should_forget(self, entry: MemoryEntry) -> tuple[bool, str]:
        """
        Decide if a memory should be forgotten/deleted.

        Criteria:
        - Expired (past TTL)
        - Low importance and old
        - Capacity cleanup needed

        Args:
            entry: Memory entry to evaluate

        Returns:
            Tuple of (should_forget, reason)
        """
        # Check expiry
        if entry.is_expired():
            return True, "Memory expired"

        # Check retention period for long-term memories
        if self._config.retention_days and entry.memory_type == MemoryType.LONG_TERM:
            age = utc_now() - entry.created_at
            if age.days > self._config.retention_days:
                # Don't delete critical memories
                if entry.importance < MemoryImportance.CRITICAL:
                    return True, f"Exceeded retention period ({self._config.retention_days} days)"

        # Check for low importance + very old + never accessed
        if (entry.importance == MemoryImportance.TRIVIAL and
            entry.access_count == 0):
            age = utc_now() - entry.created_at
            if age.days > 7:  # Old trivial memories
                return True, "Trivial and unaccessed"

        return False, "Memory should be retained"

    def find_duplicates(
        self,
        entry: MemoryEntry,
        threshold: Optional[float] = None,
        user_id: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """
        Find existing memories that are duplicates of the given entry.

        Duplicate detection is scoped to the current user to prevent
        cross-user false positives (e.g., two different users saying
        "I like Python" should not be considered duplicates).

        Args:
            entry: Memory entry to check against
            threshold: Similarity threshold (uses config default if not provided)
            user_id: User ID to scope duplicate detection (required for proper isolation)

        Returns:
            List of duplicate MemoryEntry objects
        """
        if threshold is None:
            threshold = self._config.deduplication_threshold

        # Build filters to scope search to current user
        filters: dict[str, Any] = {}
        if user_id:
            filters["user_id"] = user_id

        # For conversation memories, also scope to session
        if entry.memory_type == MemoryType.CONVERSATION and entry.session_id:
            filters["session_id"] = entry.session_id

        # Search for similar content within scoped boundaries
        candidates = self._storage.search(
            query=entry.content,
            filters=filters if filters else None,
            limit=20,
        )

        duplicates = []
        for candidate in candidates:
            if candidate.id == entry.id:
                continue

            similarity = entry.similarity_score(candidate)
            if similarity >= threshold:
                duplicates.append(candidate)

        return duplicates

    def get_cleanup_candidates(
        self,
        memory_type: Optional[MemoryType] = None,
        max_count: int = 10,
    ) -> list[MemoryEntry]:
        """
        Get memories that are candidates for cleanup.

        Args:
            memory_type: Optional filter by type
            max_count: Maximum number of candidates to return

        Returns:
            List of MemoryEntry objects to consider for deletion
        """
        entries = self._storage.get_all(memory_type=memory_type)
        candidates = []

        for entry in entries:
            should_forget, _ = self.should_forget(entry)
            if should_forget:
                candidates.append(entry)

        # Sort by priority (expired first, then low importance, then old)
        def sort_key(e: MemoryEntry):
            expiry_score = 0 if e.is_expired() else 1
            importance_score = 5 - e.importance.value  # Lower importance = higher priority
            age_score = (utc_now() - e.created_at).days
            return (expiry_score, importance_score, -age_score)

        candidates.sort(key=sort_key)
        return candidates[:max_count]

    def cleanup(self, dry_run: bool = False) -> dict[str, int]:
        """
        Perform memory cleanup.

        When dry_run=True, NO mutations occur - only statistics are returned
        describing what WOULD be cleaned.

        Args:
            dry_run: If True, don't actually delete, just report

        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "expired_removed": 0,
            "low_priority_removed": 0,
            "duplicates_removed": 0,  # Renamed from "duplicates_merged" for accuracy
            "total_freed": 0,
        }

        all_entries = self._storage.get_all()

        # Remove expired (respecting dry_run)
        for entry in all_entries:
            if entry.is_expired():
                if not dry_run:
                    self._storage.delete(entry.id)
                stats["expired_removed"] += 1
                stats["total_freed"] += 1

        # Find and remove duplicates (not merge - we just delete extras)
        seen_contents: dict[str, list[MemoryEntry]] = {}
        for entry in all_entries:
            if entry.is_expired():
                continue  # Already counted above
            normalized = entry.content.lower().strip()
            if normalized not in seen_contents:
                seen_contents[normalized] = []
            seen_contents[normalized].append(entry)

        for content, entries in seen_contents.items():
            if len(entries) > 1:
                # Keep the most important one, remove others
                entries.sort(key=lambda e: e.importance.value, reverse=True)
                keeper = entries[0]
                for dup in entries[1:]:
                    if not dry_run:
                        self._storage.delete(dup.id)
                    stats["duplicates_removed"] += 1
                    stats["total_freed"] += 1

        return stats
