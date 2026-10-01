import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from app import main
from tests import helpers


class StreamingReader(StringIO):
    def readlines(self, *args):
        raise AssertionError("whole-file reads are not allowed")

    def read(self, size=-1):
        if size != 1:
            raise AssertionError("only a one-character EOF probe is allowed")
        return super().read(size)


class BoundedReader(StreamingReader):
    def __init__(self, content, max_chars):
        super().__init__(content)
        self.max_chars = max_chars
        self.requested_sizes = []

    def readline(self, size=-1):
        if not 0 < size <= self.max_chars + 1:
            raise AssertionError("line reads must have a bounded size")
        self.requested_sizes.append(size)
        return super().readline(size)


class FileReadTests(helpers.WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.file = self.root / "example.txt"
        self.file.write_text("alpha\nbeta\ngamma\n")

    def test_default_offset_preserves_content(self):
        self.assertEqual(self.read()["content"], "alpha\nbeta\ngamma\n")

    def read(self, **arguments):
        return json.loads(self.tools.read_file("example.txt", **arguments))

    def test_offset_is_one_based(self):
        self.assertEqual(self.read(offset=2)["content"], "beta\ngamma\n")

    def test_offset_past_eof_returns_empty_content(self):
        self.assertEqual(
            self.read(offset=5),
            {
                "content": "",
                "start_line": 5,
                "end_line": None,
                "truncated": False,
                "next_offset": None,
            },
        )

    def test_limit_selects_a_section(self):
        self.assertEqual(
            self.read(offset=2, limit=1),
            {
                "content": "beta\n",
                "start_line": 2,
                "end_line": 2,
                "truncated": True,
                "next_offset": 3,
            },
        )

    def test_limit_can_extend_past_eof(self):
        self.assertEqual(self.read(offset=3, limit=10)["content"], "gamma\n")

    def test_rejects_invalid_offsets(self):
        for value in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(offset=value):
                with self.assertRaisesRegex(RuntimeError, "offset must be a positive integer"):
                    self.tools.read_file("example.txt", offset=value)

    def test_rejects_invalid_limits(self):
        for value in (0, -1, True, False, 1.5, "2", None):
            with self.subTest(limit=value):
                with self.assertRaisesRegex(RuntimeError, "limit must be a positive integer"):
                    self.tools.read_file("example.txt", limit=value)

    def test_default_line_budget(self):
        self.file.write_text("line\n" * (main.DEFAULT_READ_LINES + 1))
        result = self.read()
        self.assertEqual(len(result["content"].splitlines()), main.DEFAULT_READ_LINES)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["next_offset"], main.DEFAULT_READ_LINES + 1)

    def test_rejects_limit_above_ceiling(self):
        with self.assertRaisesRegex(RuntimeError, "limit must not exceed"):
            self.tools.read_file("example.txt", limit=main.MAX_READ_LINES + 1)

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

    def test_small_range_does_not_read_the_rest_of_file(self):
        reader = StreamingReader("alpha\nbeta\n" + "x" * 100000)
        with patch.object(main, "open", return_value=reader, create=True):
            result = self.read(limit=1)
        self.assertEqual(result["content"], "alpha\n")
        self.assertEqual(result["next_offset"], 2)

    def test_huge_selected_line_uses_bounded_reads(self):
        reader = BoundedReader("x" * 100000, max_chars=20)
        with patch.object(main, "open", return_value=reader, create=True):
            with self.assertRaisesRegex(RuntimeError, "line 1 exceeds max_chars=20"):
                self.read(max_chars=20)
        self.assertEqual(reader.requested_sizes, [21])

    def test_remaining_character_budget_bounds_next_line_read(self):
        reader = BoundedReader("alpha\n" + "x" * 100000, max_chars=8)
        with patch.object(main, "open", return_value=reader, create=True):
            result = self.read(max_chars=8)
        self.assertEqual(result["content"], "alpha\n")
        self.assertEqual(result["next_offset"], 2)
        self.assertEqual(reader.requested_sizes, [9, 3])

    def test_skips_oversized_lines_in_bounded_chunks(self):
        reader = BoundedReader("x" * 100000 + "\nbeta\ngamma\n", max_chars=10)
        with patch.object(main, "open", return_value=reader, create=True):
            result = self.read(offset=2, limit=1, max_chars=10)
        self.assertEqual(result["content"], "beta\n")
        self.assertEqual(result["next_offset"], 3)
        self.assertGreater(len(reader.requested_sizes), 9000)

    def test_huge_offset_stops_skipping_at_eof(self):
        reader = BoundedReader("alpha\n", max_chars=10)
        with patch.object(main, "open", return_value=reader, create=True):
            result = self.read(offset=10**12, max_chars=10)
        self.assertEqual(result["content"], "")
        self.assertFalse(result["truncated"])
        self.assertEqual(len(reader.requested_sizes), 3)

    def test_empty_file_has_no_range_or_continuation(self):
        self.file.write_text("")
        self.assertEqual(
            self.read(),
            {
                "content": "",
                "start_line": 1,
                "end_line": None,
                "truncated": False,
                "next_offset": None,
            },
        )

    def test_unicode_budget_counts_characters_not_bytes(self):
        self.file.write_text("é🙂\n終\n", encoding="utf-8")
        first = self.read(max_chars=3)
        self.assertEqual(first["content"], "é🙂\n")
        self.assertEqual(first["next_offset"], 2)
        self.assertEqual(self.read(offset=2, max_chars=2)["content"], "終\n")

    def test_newline_variants_use_normalized_line_numbers(self):
        for newline in (b"\n", b"\r\n", b"\r"):
            with self.subTest(newline=newline):
                self.file.write_bytes(newline.join((b"alpha", b"beta", b"gamma")))
                self.assertEqual(self.read(offset=2, limit=1)["content"], "beta\n")
                final = self.read(offset=3, max_chars=5)
                self.assertEqual(final["content"], "gamma")
                self.assertFalse(final["truncated"])

    def test_blank_lines_are_not_eof(self):
        self.file.write_text("\n\nbeta\n")
        result = self.read(limit=2, max_chars=2)
        self.assertEqual(result["content"], "\n\n")
        self.assertEqual(result["next_offset"], 3)

    def test_ranged_read_rejects_symlink_outside_workspace(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret.txt"
            target.write_text("secret\n")
            (self.root / "link.txt").symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "outside workspace"):
                self.tools.read_file("link.txt", offset=1, limit=1)

    def test_ranged_read_allows_symlink_inside_workspace(self):
        (self.root / "link.txt").symlink_to(self.file)
        result = json.loads(self.tools.read_file("link.txt", offset=2, limit=1))
        self.assertEqual(result["content"], "beta\n")

    def test_missing_file_retains_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a file"):
            self.tools.read_file("missing.txt", offset=2)

    def test_agent_receives_range_metadata_and_can_continue(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "first",
                            "read_file",
                            '{"path": "example.txt", "offset": 2, "limit": 1, "max_chars": 10}',
                        )
                    ],
                ),
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "second",
                            "read_file",
                            '{"path": "example.txt", "offset": 3, "limit": 1}',
                        )
                    ],
                ),
                helpers.assistant_message("Read beta and gamma."),
            ]
        )
        self.assertEqual(self.run_agent(client, "Read from line 2"), "Read beta and gamma.")
        first = json.loads(
            helpers.tool_result(client.completions.calls[1]["messages"], "first")["content"]
        )
        second = json.loads(
            helpers.tool_result(client.completions.calls[2]["messages"], "second")["content"]
        )
        self.assertEqual(first["content"], "beta\n")
        self.assertEqual(first["next_offset"], 3)
        self.assertEqual(second["content"], "gamma\n")
        self.assertIsNone(second["next_offset"])

    def test_agent_can_recover_from_an_oversized_line(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "small",
                            "read_file",
                            '{"path": "example.txt", "max_chars": 5}',
                        )
                    ],
                ),
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "larger",
                            "read_file",
                            '{"path": "example.txt", "max_chars": 17}',
                        )
                    ],
                ),
                helpers.assistant_message("Read all three lines."),
            ]
        )
        self.assertEqual(self.run_agent(client, "Read the file"), "Read all three lines.")
        error = helpers.tool_result(client.completions.calls[1]["messages"], "small")
        self.assertEqual(error["tool_call_id"], "small")
        self.assertIn("error: line 1 exceeds max_chars=5; increase", error["content"])
        result = json.loads(
            helpers.tool_result(client.completions.calls[2]["messages"], "larger")["content"]
        )
        self.assertEqual(result["content"], self.file.read_text())
        self.assertFalse(result["truncated"])

    def test_invalid_range_arguments_are_returned_as_tool_errors(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "invalid",
                            "read_file",
                            '{"path": "example.txt", "offset": true}',
                        )
                    ],
                ),
                helpers.assistant_message("The offset must be an integer."),
            ]
        )
        self.run_agent(client, "Read a range")
        result = helpers.tool_result(client.completions.calls[1]["messages"], "invalid")
        self.assertEqual(result["content"], "error: offset must be a positive integer")
