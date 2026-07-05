"""
tests/test_router.py

Covers core/router.py:
    - Whole-word keyword matching routes correctly for real intents.
    - Multi-word phrases ("look up") still match.
    - Falls back to DEFAULT_AGENT_ID when nothing matches.
    - Regression tests for the substring-matching bug: keywords must
      NOT match when they're only a fragment of an unrelated word
      (e.g. "code" inside "encode"/"decode"/"barcode", "search" inside
      "research"/"researching").
    - register() lets new routes be added without modifying Router.
"""

from __future__ import annotations

import unittest

from core.router import DEFAULT_AGENT_ID, Router


class TestRouterWholeWordMatching(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router()

    def test_matches_coding_agent_on_whole_word(self) -> None:
        # Uses only the "python" keyword (not "bug") so the assertion
        # on matched_keyword is deterministic regardless of dict/list
        # iteration order inside Router.
        result = self.router.route("my python script threw an exception")
        self.assertEqual(result.agent_id, "coding_agent")
        self.assertEqual(result.matched_keyword, "python")

    def test_matches_research_agent_on_multi_word_phrase(self) -> None:
        result = self.router.route("please look up the latest papers")
        self.assertEqual(result.agent_id, "research_agent")
        self.assertEqual(result.matched_keyword, "look up")

    def test_falls_back_to_default_agent(self) -> None:
        result = self.router.route("good morning, how are you?")
        self.assertEqual(result.agent_id, DEFAULT_AGENT_ID)
        self.assertIsNone(result.matched_keyword)

    def test_matching_is_case_insensitive(self) -> None:
        result = self.router.route("PYTHON crashed again")
        self.assertEqual(result.agent_id, "coding_agent")


class TestRouterFragmentFalsePositiveRegression(unittest.TestCase):
    """
    Regression tests for the substring-matching bug flagged in review:
    naive `keyword in text` matched keywords hidden inside unrelated
    words. These must now fall back to the default agent.
    """

    def setUp(self) -> None:
        self.router = Router()

    def test_decode_does_not_match_code(self) -> None:
        result = self.router.route("please decode this message")
        self.assertEqual(result.agent_id, DEFAULT_AGENT_ID)

    def test_barcode_does_not_match_code(self) -> None:
        result = self.router.route("scan this barcode")
        self.assertEqual(result.agent_id, DEFAULT_AGENT_ID)

    def test_coder_does_not_match_code(self) -> None:
        result = self.router.route("she is a great coder")
        self.assertEqual(result.agent_id, DEFAULT_AGENT_ID)

    def test_researching_does_not_match_search(self) -> None:
        result = self.router.route("I am researching AI safety")
        self.assertEqual(result.agent_id, DEFAULT_AGENT_ID)


class TestRouterRegister(unittest.TestCase):
    def test_register_adds_a_new_route_without_modifying_router(self) -> None:
        router = Router()
        router.register("finance_agent", ["invoice", "budget"])

        result = router.route("please review this invoice")
        self.assertEqual(result.agent_id, "finance_agent")
        self.assertEqual(result.matched_keyword, "invoice")


if __name__ == "__main__":
    unittest.main()
