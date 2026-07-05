"""
tests/test_logger.py

Covers core/logger.py:
    - get_logger() returns a standard library Logger.
    - configure_logging() is idempotent (safe to call more than once).
    - JsonFormatter produces valid, parseable JSON with the expected fields.
"""

from __future__ import annotations

import json
import logging
import unittest

from core.logger import JsonFormatter, configure_logging, get_logger


class TestGetLogger(unittest.TestCase):
    def test_get_logger_returns_named_logger(self) -> None:
        logger = get_logger("mahir.test.module")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "mahir.test.module")

    def test_configure_logging_is_idempotent(self) -> None:
        # Calling this multiple times must not raise or duplicate
        # handlers unboundedly.
        configure_logging(level="DEBUG")
        handlers_after_first_call = len(logging.getLogger().handlers)

        configure_logging(level="DEBUG")
        handlers_after_second_call = len(logging.getLogger().handlers)

        self.assertEqual(handlers_after_first_call, handlers_after_second_call)


class TestJsonFormatter(unittest.TestCase):
    def test_format_produces_valid_json_with_expected_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="mahir.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)  # must not raise

        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["logger"], "mahir.test")
        self.assertEqual(parsed["message"], "hello world")
        self.assertIn("timestamp", parsed)


if __name__ == "__main__":
    unittest.main()
