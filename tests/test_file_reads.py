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
        self.assertEqual(main.read_file("example.txt"), "alpha\nbeta\ngamma\n")

    def test_offset_is_one_based(self):
        self.assertEqual(main.read_file("example.txt", offset=2), "beta\ngamma\n")

    def test_offset_past_eof_returns_empty_content(self):
        self.assertEqual(main.read_file("example.txt", offset=5), "")

    def test_limit_selects_a_section(self):
        self.assertEqual(main.read_file("example.txt", offset=2, limit=1), "beta\n")

    def test_limit_can_extend_past_eof(self):
        self.assertEqual(main.read_file("example.txt", offset=3, limit=10), "gamma\n")

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
        self.assertEqual(len(main.read_file("example.txt").splitlines()), main.DEFAULT_READ_LINES)

    def test_rejects_limit_above_ceiling(self):
        with self.assertRaisesRegex(RuntimeError, "limit must not exceed"):
            main.read_file("example.txt", limit=main.MAX_READ_LINES + 1)
