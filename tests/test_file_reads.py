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
