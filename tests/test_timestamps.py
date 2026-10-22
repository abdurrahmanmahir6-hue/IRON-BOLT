"""Regression tests for timestamp parsing and request timestamp flow."""

from datetime import datetime, timezone
import unittest

from memory.models import ConversationTurn, MemoryEntry
from memory.storage import InMemoryStorage
from memory.conversation import ConversationMemory


class TimestampTests(unittest.TestCase):
    def test_memory_entry_accepts_iso_string_and_normalizes_to_utc(self):
        entry = MemoryEntry.from_dict(
            {
                "content": "legacy",
                "created_at": "2026-01-01T12:00:00",
                "updated_at": "2026-01-01T12:00:00+02:00",
            }
        )

        self.assertEqual(entry.created_at.tzinfo, timezone.utc)
        self.assertEqual(entry.updated_at.utcoffset(), timezone.utc.utcoffset(None))

    def test_memory_entry_does_not_double_parse_datetime(self):
        timestamp = datetime.now(timezone.utc)
        entry = MemoryEntry.from_dict(
            {
                "content": "already parsed",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

        self.assertEqual(entry.created_at, timestamp)

    def test_conversation_turn_retrieval_does_not_mutate_or_double_parse(self):
        data = {
            "user_message": "hello",
            "ai_response": "hi",
            "timestamp": "2026-01-01T12:00:00+00:00",
            "context": {},
        }

        first = ConversationTurn.from_dict(data)
        second = ConversationTurn.from_dict(data)

        self.assertIsInstance(first.timestamp, datetime)
        self.assertIsInstance(second.timestamp, datetime)
        self.assertIsInstance(data["timestamp"], str)

    def test_each_request_timestamp_is_preserved_separately(self):
        storage = InMemoryStorage()
        storage.initialize()
        conversation = ConversationMemory(storage)
        first_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        second_timestamp = datetime(2026, 1, 2, tzinfo=timezone.utc)

        conversation.add_turn("one", "reply one", timestamp=first_timestamp)
        conversation.add_turn("two", "reply two", timestamp=second_timestamp)
        turns = conversation.get_turns(limit=2)

        self.assertEqual([turn.timestamp for turn in turns], [first_timestamp, second_timestamp])


if __name__ == "__main__":
    unittest.main()
