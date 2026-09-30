import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import helpers
from app import main


class FileReadTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.file = self.root / "example.txt"
        self.file.write_text("alpha\nbeta\ngamma\n")
        self.workspace_patch = patch.object(main, "WORKSPACE_ROOT", self.root)
        self.workspace_patch.start()
        self.addCleanup(self.workspace_patch.stop)

    def test_default_offset_preserves_content(self):
        self.assertEqual(self.read()["content"], "alpha\nbeta\ngamma\n")

    def read(self, **arguments):
        return json.loads(main.read_file("example.txt", **arguments))

    def test_offset_is_one_based(self):
        self.assertEqual(self.read(offset=2)["content"], "beta\ngamma\n")

    def test_offset_past_eof_returns_empty_content(self):
        self.assertEqual(self.read(offset=5), {
            "content": "", "start_line": 5, "end_line": None,
            "truncated": False, "next_offset": None,
        })

    def test_limit_selects_a_section(self):
        self.assertEqual(self.read(offset=2, limit=1), {
            "content": "beta\n", "start_line": 2, "end_line": 2,
            "truncated": True, "next_offset": 3,
        })

    def test_limit_can_extend_past_eof(self):
        self.assertEqual(self.read(offset=3, limit=10)["content"], "gamma\n")

    def test_rejects_invalid_offsets(self):
        for value in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(offset=value):
                with self.assertRaisesRegex(RuntimeError, "offset must be a positive integer"):
                    main.read_file("example.txt", offset=value)

    def test_rejects_invalid_limits(self):
        for value in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(limit=value):
                with self.assertRaisesRegex(RuntimeError, "limit must be a positive integer"):
                    main.read_file("example.txt", limit=value)

    def test_default_line_budget(self):
        self.file.write_text("line\n" * (main.DEFAULT_READ_LINES + 1))
        result = self.read()
        self.assertEqual(len(result["content"].splitlines()), main.DEFAULT_READ_LINES)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["next_offset"], main.DEFAULT_READ_LINES + 1)

    def test_rejects_limit_above_ceiling(self):
        with self.assertRaisesRegex(RuntimeError, "limit must not exceed"):
            main.read_file("example.txt", limit=main.MAX_READ_LINES + 1)

    def test_exact_line_boundary_is_not_truncated(self):
        result = self.read(limit=3)
        self.assertFalse(result["truncated"])
        self.assertIsNone(result["next_offset"])
        self.assertEqual(result["end_line"], 3)

    def test_continuation_reconstructs_file_without_gaps(self):
        first = self.read(limit=2)
        second = self.read(offset=first["next_offset"], limit=2)
        self.assertEqual(first["content"] + second["content"], self.file.read_text())
        self.assertFalse(second["truncated"])

    def test_character_budget_preserves_complete_lines(self):
        first = self.read(max_chars=8)
        self.assertEqual(first["content"], "alpha\n")
        self.assertEqual(first["next_offset"], 2)
        second = self.read(offset=2, max_chars=11)
        self.assertEqual(first["content"] + second["content"], self.file.read_text())

    def test_exact_character_boundary_is_not_truncated(self):
        self.assertFalse(self.read(max_chars=17)["truncated"])

    def test_oversized_first_line_gives_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, "line 1 exceeds max_chars=5; increase"):
            self.read(max_chars=5)

    def test_rejects_invalid_character_budgets(self):
        for value in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(max_chars=value):
                with self.assertRaisesRegex(RuntimeError, "max_chars must be a positive integer"):
                    self.read(max_chars=value)
        with self.assertRaisesRegex(RuntimeError, "max_chars must not exceed"):
            self.read(max_chars=main.MAX_READ_CHARS + 1)

    def test_default_character_budget(self):
        self.file.write_text(("x" * 999 + "\n") * 20)
        result = self.read()
        self.assertEqual(len(result["content"]), main.DEFAULT_READ_CHARS)
        self.assertEqual(result["next_offset"], 17)
