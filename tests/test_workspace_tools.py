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

    def listing(self, **arguments):
        return json.loads(main.list_files(".", **arguments))

    def test_listing_returns_sorted_selected_entries(self):
        self.make_entries()
        self.assertEqual(self.listing(offset=2, limit=1)["entries"], ["beta"])
        self.assertEqual(self.listing(limit=3)["entries"], ["alpha", "beta", "gamma"])
        self.assertEqual(self.listing(offset=4)["entries"], [])

    def test_listing_preserves_names_at_character_boundaries(self):
        self.make_entries()
        self.assertEqual(self.listing(max_chars=9)["entries"], ["alpha", "beta"])
        self.assertEqual(self.listing(max_chars=8)["entries"], ["alpha"])
        with self.assertRaisesRegex(RuntimeError, "entry name exceeds max_chars"):
            main.list_files(".", max_chars=4)

    def test_listing_default_entry_limit(self):
        for index in range(main.DEFAULT_LIST_ENTRIES + 1):
            (self.root / f"entry_{index:03}").touch()
        self.assertEqual(len(self.listing()["entries"]), main.DEFAULT_LIST_ENTRIES)

    def test_listing_continuation_reconstructs_entries(self):
        self.make_entries()
        first = self.listing(max_chars=9)
        self.assertTrue(first["truncated"])
        self.assertEqual(first["next_offset"], 3)
        second = self.listing(offset=first["next_offset"])
        self.assertEqual(first["entries"] + second["entries"], ["alpha", "beta", "gamma"])
        self.assertFalse(second["truncated"])
        self.assertIsNone(second["next_offset"])

    def test_listing_schema_matches_runtime_budgets(self):
        tool = next(tool for tool in main.TOOLS if tool["function"]["name"] == "list_files")
        parameters = tool["function"]["parameters"]
        self.assertEqual(parameters["required"], ["path"])
        self.assertFalse(parameters["additionalProperties"])
        for name, default, ceiling in (
            ("limit", main.DEFAULT_LIST_ENTRIES, main.MAX_LIST_ENTRIES),
            ("max_chars", main.DEFAULT_TOOL_CHARS, main.MAX_TOOL_CHARS),
        ):
            field = parameters["properties"][name]
            self.assertEqual((field["type"], field["minimum"]), ("integer", 1))
            self.assertEqual((field["default"], field["maximum"]), (default, ceiling))

    def test_empty_listing_and_offset_past_end_have_no_continuation(self):
        expected = {"entries": [], "truncated": False, "next_offset": None}
        self.assertEqual(self.listing(), expected)
        self.make_entries()
        self.assertEqual(self.listing(offset=10**12), expected)

    def test_listing_exact_limits_do_not_claim_truncation(self):
        self.make_entries()
        result = self.listing(limit=3, max_chars=14)
        self.assertFalse(result["truncated"])
        self.assertIsNone(result["next_offset"])

    def test_agent_receives_and_continues_listing_pages(self):
        self.make_entries()
        client = helpers.FakeClient([
            helpers.assistant_message(None, [helpers.tool_call(
                "first", "list_files", '{"path": ".", "limit": 2}',
            )]),
            helpers.assistant_message(None, [helpers.tool_call(
                "second", "list_files", '{"path": ".", "offset": 3, "limit": 2}',
            )]),
            helpers.assistant_message("Found alpha, beta, and gamma."),
        ])
        self.assertEqual(main.run_agent(client, "List entries"), "Found alpha, beta, and gamma.")
        first = json.loads(client.completions.calls[1]["messages"][2]["content"])
        second = json.loads(client.completions.calls[2]["messages"][4]["content"])
        self.assertEqual(first["next_offset"], 3)
        self.assertEqual(first["entries"] + second["entries"], ["alpha", "beta", "gamma"])
        self.assertFalse(second["truncated"])

    def test_listing_budget_error_is_returned_to_agent(self):
        self.make_entries()
        client = helpers.FakeClient([
            helpers.assistant_message(None, [helpers.tool_call(
                "small", "list_files", '{"path": ".", "max_chars": 1}',
            )]),
            helpers.assistant_message("Increase the name budget."),
        ])
        main.run_agent(client, "List entries")
        self.assertEqual(client.completions.calls[1]["messages"][2]["content"],
                         "error: entry name exceeds max_chars; increase max_chars")
