import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import helpers
from app import main


class WorkspaceToolTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        workspace_patch = patch.object(main, "WORKSPACE_ROOT", self.root)
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)

    def test_listing_rejects_invalid_ranges_and_budgets(self):
        for name in ("offset", "limit", "max_chars"):
            for value in (0, -1, True, False, 1.5, "1", None):
                with self.subTest(argument=name, value=value):
                    with self.assertRaisesRegex(RuntimeError, f"{name} must be a positive integer"):
                        main.list_files(".", **{name: value})
        for name, maximum in (("limit", main.MAX_LIST_ENTRIES), ("max_chars", main.MAX_TOOL_CHARS)):
            with self.assertRaisesRegex(RuntimeError, f"{name} must not exceed"):
                main.list_files(".", **{name: maximum + 1})

    def test_listing_rejects_invalid_paths(self):
        for path in (None, 1, False, [], "", "bad\0path"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError, "path must"):
                    main.list_files(path)
