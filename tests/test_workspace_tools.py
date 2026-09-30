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

    def make_entries(self):
        for name in ("gamma", "alpha", "beta"):
            (self.root / name).touch()

    def test_listing_returns_sorted_selected_entries(self):
        self.make_entries()
        self.assertEqual(main.list_files(".", offset=2, limit=1), "beta")
        self.assertEqual(main.list_files(".", limit=3), "alpha\nbeta\ngamma")
        self.assertEqual(main.list_files(".", offset=4), "")

    def test_listing_preserves_names_at_character_boundaries(self):
        self.make_entries()
        self.assertEqual(main.list_files(".", max_chars=9), "alpha\nbeta")
        self.assertEqual(main.list_files(".", max_chars=8), "alpha")
        with self.assertRaisesRegex(RuntimeError, "entry name exceeds max_chars"):
            main.list_files(".", max_chars=4)

    def test_listing_default_entry_limit(self):
        for index in range(main.DEFAULT_LIST_ENTRIES + 1):
            (self.root / f"entry_{index:03}").touch()
        self.assertEqual(len(main.list_files(".").splitlines()), main.DEFAULT_LIST_ENTRIES)
