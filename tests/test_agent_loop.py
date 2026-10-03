import json
import unittest
from io import StringIO
from unittest.mock import patch

from app import main
from tests.helpers import (
    FakeClient,
    WorkspaceTestCase,
    assistant_message,
    final_message_without_tool_calls,
    fixture_text,
    tool_call,
    tool_result,
)


class AgentLoopTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        (self.root / "README.md").write_text("# Claude Code Python Agent\n")
        (self.root / "app").mkdir()

    def test_run_agent_returns_final_answer_without_tool_calls(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([assistant_message(final_answer)])

        self.assertEqual(self.run_agent(client, "Say hello"), final_answer)
        self.assertEqual(len(client.completions.calls), 1)

    def test_run_agent_handles_final_answer_without_tool_calls_attribute(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([final_message_without_tool_calls(final_answer)])

        self.assertEqual(self.run_agent(client, "Say hello"), final_answer)

    def test_run_agent_reads_file_then_returns_generated_answer(self):
        final_answer = fixture_text("readme_summary.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "read_file", '{"path": "README.md"}')],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Summarize the README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[1].tool_calls[0].id, "call_1")
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertIn(
            "Claude Code Python Agent", tool_result(second_call_messages, "call_1")["content"]
        )

    def test_run_agent_can_process_multiple_tool_rounds(self):
        final_answer = fixture_text("workspace_listing_answer.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "list_files", '{"path": "."}')],
                ),
                assistant_message(
                    None,
                    [tool_call("call_2", "read_file", '{"path": "README.md"}')],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Inspect the workspace"), final_answer)
        self.assertEqual(len(client.completions.calls), 3)

        final_call_messages = client.completions.calls[2]["messages"]
        tool_results = [
            message
            for message in final_call_messages
            if isinstance(message, dict) and message["role"] == "tool"
        ]

        self.assertEqual(
            [message["tool_call_id"] for message in tool_results], ["call_1", "call_2"]
        )
        self.assertIn("README.md", tool_result(final_call_messages, "call_1")["content"])
        self.assertIn(
            "Claude Code Python Agent", tool_result(final_call_messages, "call_2")["content"]
        )

    def test_run_agent_can_process_edit_file_tool_call(self):
        final_answer = fixture_text("edit_file_answer.txt")

        file_path = self.root / "example.txt"
        file_path.write_text("hello world")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [
                        tool_call(
                            "call_1",
                            "edit_file",
                            '{"path": "example.txt", "old_text": "world", "new_text": "agent"}',
                        )
                    ],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Update example.txt"), final_answer)
        self.assertEqual(file_path.read_text(), "hello agent")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(
            json.loads(tool_result(second_call_messages, "call_1")["content"]),
            {
                "status": "updated",
                "path": "example.txt",
                "replacements": 1,
            },
        )

    def test_run_agent_returns_tool_errors_to_model(self):
        final_answer = fixture_text("tool_error_answer.txt")

        file_path = self.root / "example.txt"
        file_path.write_text("hello world")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [
                        tool_call(
                            "call_1",
                            "edit_file",
                            '{"path": "example.txt", "old_text": "missing", "new_text": "agent"}',
                        )
                    ],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Update example.txt"), final_answer)
        self.assertEqual(file_path.read_text(), "hello world")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(
            tool_result(second_call_messages, "call_1")["content"], "error: old_text not found"
        )

    def test_run_agent_returns_malformed_tool_arguments_to_model(self):
        final_answer = fixture_text("tool_error_answer.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "read_file", '{"path": "README.md"')],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Read the README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertIn("error:", tool_result(second_call_messages, "call_1")["content"])

    def test_run_agent_returns_unknown_tool_errors_to_model(self):
        final_answer = fixture_text("tool_error_answer.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "delete_file", '{"path": "README.md"}')],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Delete README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(
            tool_result(second_call_messages, "call_1")["content"],
            "error: unknown tool: delete_file",
        )

    def test_run_agent_can_process_create_file_tool_call(self):
        final_answer = fixture_text("create_file_answer.txt")

        file_path = self.root / "notes.txt"
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [
                        tool_call(
                            "call_1",
                            "create_file",
                            '{"path": "notes.txt", "content": "hello agent"}',
                        )
                    ],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Create notes.txt"), final_answer)
        self.assertEqual(file_path.read_text(), "hello agent")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(
            json.loads(tool_result(second_call_messages, "call_1")["content"]),
            {
                "status": "created",
                "path": "notes.txt",
                "chars_written": 11,
            },
        )

    def test_run_agent_can_process_search_files_tool_call(self):
        final_answer = fixture_text("search_files_answer.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "search_files", '{"query": "Claude", "path": "."}')],
                ),
                assistant_message(final_answer),
            ]
        )

        self.assertEqual(self.run_agent(client, "Search for Claude"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertIn("README.md", tool_result(second_call_messages, "call_1")["content"])

    def test_run_agent_logs_tool_calls_in_verbose_mode(self):
        final_answer = fixture_text("readme_summary.txt")
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "read_file", '{"path": "README.md"}')],
                ),
                assistant_message(final_answer),
            ]
        )
        stderr = StringIO()

        with patch("sys.stderr", stderr):
            self.assertEqual(self.run_agent(client, "Read README", verbose=True), final_answer)

        self.assertIn("Using read_file path=README.md", stderr.getvalue())
        self.assertIn("Tool result: ok", stderr.getvalue())

    def test_format_tool_call_reports_invalid_json(self):
        formatted = main.format_tool_call(tool_call("call_1", "read_file", "{"))

        self.assertEqual(formatted, "Using read_file with invalid JSON arguments")

    def test_verbose_malformed_calls_return_errors_and_continue(self):
        invalid_calls = [
            ("read_file", "{", "invalid JSON arguments"),
            ("read_file", "[]", "arguments for read_file must be a JSON object"),
            ("read_file", "null", "arguments for read_file must be a JSON object"),
            ("read_file", '"text"', "arguments for read_file must be a JSON object"),
            ("read_file", "{}", "invalid arguments for read_file"),
            ("read_file", '{"path": "README.md", "extra": 1}', "invalid arguments"),
            ("missing", "{}", "unknown tool: missing"),
            ("", "{}", "tool name must be a nonempty string"),
        ]
        for name, arguments, error in invalid_calls:
            with self.subTest(name=name, arguments=arguments):
                client = FakeClient(
                    [
                        assistant_message(
                            None,
                            [
                                tool_call("bad", name, arguments),
                                tool_call("good", "read_file", '{"path": "README.md"}'),
                            ],
                        ),
                        assistant_message("Recovered"),
                    ]
                )
                stderr = StringIO()
                with patch("sys.stderr", stderr):
                    self.assertEqual(
                        self.run_agent(client, "Read README", verbose=True), "Recovered"
                    )
                messages = client.completions.calls[1]["messages"]
                self.assertIn(f"error: {error}", tool_result(messages, "bad")["content"])
                self.assertIn("Claude Code Python Agent", tool_result(messages, "good")["content"])
                self.assertIn(f"Tool result: error: {error}", stderr.getvalue())

    def test_verbose_tool_arguments_are_decoded_once(self):
        messages = []
        message = assistant_message(
            None, [tool_call("call_1", "read_file", '{"path": "README.md"}')]
        )
        with (
            patch("app.registry.json.loads", wraps=json.loads) as decode,
            patch("sys.stderr", StringIO()),
        ):
            main.append_tool_results(messages, message, verbose=True)
        argument_decodes = [
            call for call in decode.call_args_list if call.args == ('{"path": "README.md"}',)
        ]
        self.assertEqual(len(argument_decodes), 1)
        self.assertIn("Claude Code Python Agent", tool_result(messages, "call_1")["content"])

    def test_summarize_tool_result_reports_line_count(self):
        self.assertEqual(main.summarize_tool_result("one\ntwo"), "ok (2 lines)")

    def test_summarize_tool_result_preserves_errors(self):
        self.assertEqual(
            main.summarize_tool_result("error: old_text not found"),
            "error: old_text not found",
        )

    def test_run_agent_respects_max_tool_rounds(self):
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [tool_call("call_1", "read_file", '{"path": "README.md"}')],
                )
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "exceeded maximum tool call rounds"):
            self.run_agent(client, "Read README", max_tool_rounds=1)

    def test_run_agent_passes_selected_model_to_chat_completion(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([assistant_message(final_answer)])

        self.assertEqual(self.run_agent(client, "Say hello", model="test/model"), final_answer)

        self.assertEqual(client.completions.calls[0]["model"], "test/model")


if __name__ == "__main__":
    unittest.main()
