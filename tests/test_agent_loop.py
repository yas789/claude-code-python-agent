import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.helpers import (
    FakeClient,
    assistant_message,
    final_message_without_tool_calls,
    fixture_text,
    tool_call,
)

from app import main


class AgentLoopTests(unittest.TestCase):
    def test_run_agent_returns_final_answer_without_tool_calls(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([assistant_message(final_answer)])

        self.assertEqual(main.run_agent(client, "Say hello"), final_answer)
        self.assertEqual(len(client.completions.calls), 1)

    def test_run_agent_handles_final_answer_without_tool_calls_attribute(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([final_message_without_tool_calls(final_answer)])

        self.assertEqual(main.run_agent(client, "Say hello"), final_answer)

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

        self.assertEqual(main.run_agent(client, "Summarize the README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[1].tool_calls[0].id, "call_1")
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertIn("Build Your own Claude Code", second_call_messages[2]["content"])

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

        self.assertEqual(main.run_agent(client, "Inspect the workspace"), final_answer)
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
        self.assertIn("README.md", tool_results[0]["content"])
        self.assertIn("Build Your own Claude Code", tool_results[1]["content"])

    def test_run_agent_can_process_edit_file_tool_call(self):
        final_answer = fixture_text("edit_file_answer.txt")

        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
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

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                self.assertEqual(main.run_agent(client, "Update example.txt"), final_answer)

            self.assertEqual(file_path.read_text(), "hello agent")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertEqual(second_call_messages[2]["content"], "updated example.txt")

    def test_run_agent_returns_tool_errors_to_model(self):
        final_answer = fixture_text("tool_error_answer.txt")

        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
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

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                self.assertEqual(main.run_agent(client, "Update example.txt"), final_answer)

            self.assertEqual(file_path.read_text(), "hello world")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertEqual(second_call_messages[2]["content"], "error: old_text not found")

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

        self.assertEqual(main.run_agent(client, "Read the README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertIn("error:", second_call_messages[2]["content"])

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

        self.assertEqual(main.run_agent(client, "Delete README"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertEqual(second_call_messages[2]["content"], "error: unknown tool: delete_file")

    def test_run_agent_can_process_create_file_tool_call(self):
        final_answer = fixture_text("create_file_answer.txt")

        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "notes.txt"
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

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                self.assertEqual(main.run_agent(client, "Create notes.txt"), final_answer)

            self.assertEqual(file_path.read_text(), "hello agent")

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertEqual(second_call_messages[2]["content"], "created notes.txt")

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

        self.assertEqual(main.run_agent(client, "Search for Claude"), final_answer)

        second_call_messages = client.completions.calls[1]["messages"]
        self.assertEqual(second_call_messages[2]["role"], "tool")
        self.assertEqual(second_call_messages[2]["tool_call_id"], "call_1")
        self.assertIn("README.md", second_call_messages[2]["content"])

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
            self.assertEqual(main.run_agent(client, "Read README", verbose=True), final_answer)

        self.assertIn('Tool: read_file {"path": "README.md"}', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
