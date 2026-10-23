"""Focused security tests for the built-in calculator and file tools."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from tools.tool_manager import CalculatorTool, FileTool


class TestCalculatorToolSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = CalculatorTool()

    def test_allows_basic_arithmetic(self) -> None:
        result = self.tool.execute(expression="(2 + 3) * 4 - 5 / 2")

        self.assertTrue(result.success)
        self.assertEqual(result.data, 17.5)

    def test_rejects_calls_attributes_and_imports(self) -> None:
        for expression in ("abs(1)", "(1).__class__", "__import__('os')"):
            with self.subTest(expression=expression):
                result = self.tool.execute(expression=expression)
                self.assertFalse(result.success)


class TestFileToolWorkspaceBoundary(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        self.outside = Path(self.temp_dir.name) / "outside.txt"
        self.outside.write_text("secret", encoding="utf-8")
        self.tool = FileTool(workspace_root=self.workspace)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_allows_relative_path_inside_workspace(self) -> None:
        result = self.tool.execute(action="write", path="notes.txt", content="allowed")

        self.assertTrue(result.success)
        self.assertEqual((self.workspace / "notes.txt").read_text(encoding="utf-8"), "allowed")

    def test_rejects_parent_path_traversal(self) -> None:
        result = self.tool.execute(action="read", path="../outside.txt")

        self.assertFalse(result.success)
        self.assertFalse("secret" in (result.error or ""))

    def test_rejects_absolute_path_outside_workspace(self) -> None:
        result = self.tool.execute(action="read", path=str(self.outside.resolve()))

        self.assertFalse(result.success)

    def test_rejects_symlink_to_outside_workspace_when_supported(self) -> None:
        link = self.workspace / "outside-link"
        try:
            os.symlink(self.outside, link)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"Symlinks are unavailable in this environment: {exc}")

        result = self.tool.execute(action="read", path="outside-link")

        self.assertFalse(result.success)

    def test_fails_closed_without_an_approved_workspace_root(self) -> None:
        result = FileTool().execute(action="read", path="notes.txt")

        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
