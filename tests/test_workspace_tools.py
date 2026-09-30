import json
import tempfile
import unittest
from pathlib import Path
from io import StringIO
from unittest.mock import patch

from tests import helpers
from app import main


class SearchReader(StringIO):
    def read(self, *args):
        raise AssertionError("search must not use whole-file reads")

    def readlines(self, *args):
        raise AssertionError("search must not use whole-file reads")

    def readline(self, size=-1):
        if not 0 < size <= main.SEARCH_CHUNK_CHARS:
            raise AssertionError("search line reads must be bounded")
        return super().readline(size)


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

    def test_search_rejects_invalid_queries(self):
        for query in (None, False, 1, [], "", "a\nb", "a\rb", "x" * (main.MAX_SEARCH_QUERY + 1)):
            with self.subTest(query=repr(query)[:30]):
                with self.assertRaisesRegex(RuntimeError, "query must"):
                    main.search_files(query, ".")

    def test_search_rejects_invalid_paths_and_budgets(self):
        for path in (None, False, "", "bad\0path"):
            with self.assertRaisesRegex(RuntimeError, "path must"):
                main.search_files("target", path)
        for name in ("limit", "max_chars"):
            for value in (0, -1, True, None, "1", 1.5):
                with self.subTest(argument=name, value=value):
                    with self.assertRaisesRegex(RuntimeError, f"{name} must be a positive integer"):
                        main.search_files("target", ".", **{name: value})
        for name, maximum in (("limit", main.SEARCH_RESULT_CEILING), ("max_chars", main.MAX_TOOL_CHARS)):
            with self.assertRaisesRegex(RuntimeError, f"{name} must not exceed"):
                main.search_files("target", ".", **{name: maximum + 1})

    def test_search_uses_custom_result_and_character_budgets(self):
        (self.root / "example.txt").write_text("target one\ntarget two\n")
        self.assertEqual(len(self.search(limit=1)["results"]), 1)
        result = self.search(max_chars=3)
        self.assertEqual(result["results"], [{
            "path": "example.txt", "line": 1, "text": "tar", "text_truncated": True,
        }])
        self.assertTrue(result["truncated"])

    def search(self, query="target", **arguments):
        return json.loads(main.search_files(query, ".", **arguments))

    def test_search_skips_files_and_directories_linked_outside_workspace(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret.txt"
            target.write_text("target secret")
            (self.root / "outside.txt").symlink_to(target)
            (self.root / "outside_dir").symlink_to(Path(outside), target_is_directory=True)
            self.assertEqual(self.search()["results"], [])

    def test_search_allows_internal_file_links_and_skips_broken_links(self):
        (self.root / "source.txt").write_text("target")
        (self.root / "alias.txt").symlink_to(self.root / "source.txt")
        (self.root / "broken.txt").symlink_to(self.root / "missing.txt")
        result = self.search()["results"]
        self.assertEqual([match["path"] for match in result], ["alias.txt", "source.txt"])

    def test_search_prunes_ignored_directories_before_visiting(self):
        for name in main.IGNORED_SEARCH_DIRS:
            directory = self.root / name
            directory.mkdir()
            (directory / "ignored.txt").write_text("target")
        directory = self.root / "visible"
        directory.mkdir()
        (directory / "found.txt").write_text("target")
        original_walk = main.os.walk
        visited = []

        def tracking_walk(*args, **kwargs):
            for entry in original_walk(*args, **kwargs):
                visited.append(Path(entry[0]))
                yield entry

        with patch.object(main.os, "walk", side_effect=tracking_walk):
            result = main.search_files("target", ".")
        self.assertEqual(visited, [self.root.resolve(), directory.resolve()])
        self.assertEqual(json.loads(result)["results"][0]["path"], "visible/found.txt")

    def test_streamed_search_matches_across_chunk_boundaries(self):
        content = "x" * (main.SEARCH_CHUNK_CHARS - 3) + "target\nnext target\n"
        reader = SearchReader(content)
        matches = list(main.iter_matching_lines(reader, "target", 10))
        self.assertEqual(matches, [(1, "x" * 10, True), (2, "next targe", True)])

    def test_streamed_search_does_not_match_across_lines(self):
        reader = SearchReader("tar\nget\nTARGET\n")
        self.assertEqual(list(main.iter_matching_lines(reader, "target", 10)), [])

    def test_streamed_search_handles_single_character_queries_and_final_lines(self):
        reader = SearchReader("a" * 100000 + "z")
        self.assertEqual(list(main.iter_matching_lines(reader, "z", 5)), [(1, "aaaaa", True)])

    def test_search_uses_bounded_reader_integration(self):
        (self.root / "example.txt").touch()
        reader = SearchReader("x" * 100000 + "target")
        with patch.object(main, "open", return_value=reader, create=True):
            result = main.search_files("target", ".", max_chars=5)
        match = json.loads(result)["results"][0]
        self.assertEqual((match["path"], match["line"], match["text"]), ("example.txt", 1, "xxxxx"))
        self.assertTrue(match["text_truncated"])

    def test_search_separates_page_truncation_from_snippet_clipping(self):
        (self.root / "example.txt").write_text("target text")
        result = self.search(max_chars=6)
        self.assertFalse(result["truncated"])
        self.assertTrue(result["results"][0]["text_truncated"])

    def test_search_schema_matches_runtime_budgets(self):
        tool = next(tool for tool in main.TOOLS if tool["function"]["name"] == "search_files")
        parameters = tool["function"]["parameters"]
        self.assertEqual(parameters["required"], ["query", "path"])
        self.assertFalse(parameters["additionalProperties"])
        properties = parameters["properties"]
        self.assertEqual(properties["query"]["maxLength"], main.MAX_SEARCH_QUERY)
        for name, default, ceiling in (
            ("limit", main.MAX_SEARCH_RESULTS, main.SEARCH_RESULT_CEILING),
            ("max_chars", main.DEFAULT_TOOL_CHARS, main.MAX_TOOL_CHARS),
        ):
            self.assertEqual(properties[name]["default"], default)
            self.assertEqual(properties[name]["maximum"], ceiling)
