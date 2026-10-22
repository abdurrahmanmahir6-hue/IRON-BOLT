"""
Memory Utility Functions

Helper functions for memory operations including similarity calculations,
text processing, and common utilities.
"""

import re
from typing import Optional
from datetime import datetime, timedelta

from .models import as_utc_datetime, utc_now


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison and storage.

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text (lowercase, stripped, single spaces)
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def calculate_similarity(text1: str, text2: str, method: str = "jaccard") -> float:
    """
    Calculate similarity between two text strings.

    Args:
        text1: First text string
        text2: Second text string
        method: Similarity method ('jaccard', 'cosine', 'exact')

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not text1 or not text2:
        return 0.0

    t1 = normalize_text(text1)
    t2 = normalize_text(text2)

    if method == "exact":
        return 1.0 if t1 == t2 else 0.0

    if method == "jaccard":
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    # Default to jaccard
    return calculate_similarity(text1, text2, "jaccard")


def is_duplicate(
    new_content: str,
    existing_content: str,
    threshold: float = 0.85,
) -> bool:
    """
    Check if new content is a duplicate of existing content.

    Args:
        new_content: New memory content
        existing_content: Existing memory content to compare against
        threshold: Similarity threshold (0-1) above which content is considered duplicate

    Returns:
        True if content is considered duplicate, False otherwise
    """
    similarity = calculate_similarity(new_content, existing_content)
    return similarity >= threshold


def generate_expiry_timestamp(ttl_seconds: Optional[int]) -> Optional[datetime]:
    """
    Generate an expiry timestamp based on TTL.

    Args:
        ttl_seconds: Time-to-live in seconds (None for no expiry)

    Returns:
        Expiry datetime or None if no expiry
    """
    if ttl_seconds is None:
        return None
    return utc_now() + timedelta(seconds=ttl_seconds)


def is_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if a timestamp has expired.

    Args:
        expires_at: Expiry timestamp

    Returns:
        True if expired, False otherwise
    """
    if expires_at is None:
        return False
    return utc_now() > (as_utc_datetime(expires_at) or utc_now())


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    Extract potential keywords from text for tagging.

    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to extract

    Returns:
        List of extracted keywords
    """
    if not text:
        return []

    # Simple keyword extraction: remove stopwords and get significant words
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "am",
        "isnt",
        "arent",
        "wasnt",
        "werent",
        "hasnt",
        "havent",
        "hadnt",
        "doesnt",
        "dont",
        "didnt",
        "wont",
        "wouldnt",
        "couldnt",
        "shouldnt",
        "cant",
        "cannot",
    }

    # Extract words (alphanumeric only)
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower())

    # Filter stopwords and count frequency
    word_freq: dict[str, int] = {}
    for word in words:
        if word not in stopwords and len(word) > 2:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in sorted_keywords[:max_keywords]]


def format_memory_summary(memories: list, max_items: int = 5) -> str:
    """
    Format a list of memories into a human-readable summary.

    Args:
        memories: List of MemoryEntry objects
        max_items: Maximum number of items to include

    Returns:
        Formatted summary string
    """
    if not memories:
        return "No memories found."

    limited = memories[:max_items]
    summary_lines = []

    for i, mem in enumerate(limited, 1):
        content_preview = (
            mem.content[:100] + "..." if len(mem.content) > 100 else mem.content
        )
        summary_lines.append(
            f"{i}. [{mem.memory_type.value}] {content_preview} (importance: {mem.importance.value})"
        )

    if len(memories) > max_items:
        summary_lines.append(f"... and {len(memories) - max_items} more memories")

    return "\n".join(summary_lines)


def validate_memory_content(content: str, min_length: int = 1, max_length: int = 10000) -> tuple[bool, str]:
    """
    Validate memory content.

    Args:
        content: Content to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return False, "Memory content cannot be empty"

    if len(content) < min_length:
        return False, f"Memory content too short (min {min_length} characters)"

    if len(content) > max_length:
        return False, f"Memory content too long (max {max_length} characters)"

    return True, ""
