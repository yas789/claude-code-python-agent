import json
import unittest

from app.diagnostics import MAX_SUMMARY_CHARS, format_tool_call, summarize_tool_result
from app.registry import ParsedToolCall
from tests.helpers import tool_call


class DiagnosticsTests(unittest.TestCase):
    def test_large_arguments_are_bounded_and_content_is_hidden(self):
        arguments = {name: "secret" * 100_000 for name in ("old_text", "new_text", "content")}
        arguments.update(path="p" * 100_000, query="q" * 100_000)
        summary = format_tool_call(ParsedToolCall("edit_file", arguments))
        self.assertLessEqual(len(summary), MAX_SUMMARY_CHARS)
        self.assertNotIn("secret", summary)
        self.assertIn("old_text=600000 chars", summary)
        self.assertIn("...", summary)

    def test_small_path_and_malformed_json_are_preserved(self):
        self.assertEqual(
            format_tool_call(tool_call("1", "read_file", '{"path":"README.md"}')),
            "Using read_file path=README.md",
        )
        self.assertEqual(
            format_tool_call(tool_call("1", "read_file", "{")),
            "Using read_file with invalid JSON arguments",
        )

    def test_json_summaries_report_counts_ranges_and_truncation(self):
        cases = [
            ({"entries": ["secret"] * 4, "truncated": True}, "ok (4 entries, truncated=True)"),
            (
                {"results": [{"text": "secret"}], "truncated": False},
                "ok (1 results, truncated=False)",
            ),
            (
                {"content": "secret", "start_line": 2, "end_line": 5, "truncated": True},
                "ok (lines 2-5, truncated=True)",
            ),
            ({"status": "updated", "path": "secret"}, "ok (updated)"),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(summarize_tool_result(json.dumps(data)), expected)

    def test_text_fallback_and_errors(self):
        self.assertEqual(summarize_tool_result("one\ntwo"), "ok (2 lines)")
        self.assertEqual(summarize_tool_result("error: bad path"), "error: bad path")
        self.assertLessEqual(
            len(summarize_tool_result("error: " + "x" * 100_000)), MAX_SUMMARY_CHARS
        )
