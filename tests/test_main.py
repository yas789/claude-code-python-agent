import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.modules["openai"] = SimpleNamespace(OpenAI=object)

from app import main


FIXTURES = Path(__file__).parent / "fixtures"


class FakeCompletions:
    def __init__(self, messages):
        self.messages = messages
        self.calls = []

    def create(self, model, messages, tools):
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        return SimpleNamespace(choices=[SimpleNamespace(message=self.messages.pop(0))])


class FakeClient:
    def __init__(self, messages):
        self.completions = FakeCompletions(messages)
        self.chat = SimpleNamespace(completions=self.completions)


def fixture_text(name):
    return (FIXTURES / name).read_text().strip()


def assistant_message(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class MainTests(unittest.TestCase):
    def test_read_file_tool_is_advertised_to_the_llm(self):
        tool_names = [tool["function"]["name"] for tool in main.TOOLS]

        self.assertIn("read_file", tool_names)

    def test_read_file_tool_description_mentions_local_workspace(self):
        tool = main.TOOLS[0]

        self.assertIn("local workspace", tool["function"]["description"])

    def test_read_file_tool_requires_path_argument(self):
        tool = main.TOOLS[0]

        self.assertEqual(tool["function"]["parameters"]["required"], ["path"])

    def test_read_file_tool_has_matching_python_function(self):
        self.assertIs(main.TOOL_FUNCTIONS["read_file"], main.read_file)

    def test_every_advertised_tool_has_a_python_function(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(advertised_tool_names, set(main.TOOL_FUNCTIONS))

    def test_every_python_tool_is_advertised_to_the_llm(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(set(main.TOOL_FUNCTIONS), advertised_tool_names)

    def test_tool_loop_has_a_maximum_round_limit(self):
        self.assertGreater(main.MAX_TOOL_ROUNDS, 0)

    def test_read_file_can_read_workspace_file(self):
        self.assertIn("Build Your own Claude Code", main.read_file("README.md"))

    def test_read_file_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            main.read_file("../README.md")

    def test_list_files_lists_workspace_entries(self):
        files = main.list_files(".")

        self.assertIn("README.md", files)
        self.assertIn("app", files)

    def test_list_files_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            main.list_files("..")

    def test_edit_file_replaces_exact_text_once(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello world")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                result = main.edit_file("example.txt", "world", "agent")

            self.assertEqual(result, "updated example.txt")
            self.assertEqual(file_path.read_text(), "hello agent")

    def test_edit_file_rejects_missing_old_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello world")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "old_text not found"):
                    main.edit_file("example.txt", "missing", "agent")

    def test_edit_file_rejects_duplicate_old_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello hello")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "old_text appears multiple times"):
                    main.edit_file("example.txt", "hello", "agent")

    def test_edit_file_rejects_parent_directory_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "outside workspace"):
                    main.edit_file("../example.txt", "old", "new")

    def test_run_agent_returns_final_answer_without_tool_calls(self):
        final_answer = fixture_text("final_answer.txt")
        client = FakeClient([assistant_message(final_answer)])

        self.assertEqual(main.run_agent(client, "Say hello"), final_answer)
        self.assertEqual(len(client.completions.calls), 1)

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
        tool_results = [message for message in final_call_messages if isinstance(message, dict) and message["role"] == "tool"]

        self.assertEqual([message["tool_call_id"] for message in tool_results], ["call_1", "call_2"])
        self.assertIn("README.md", tool_results[0]["content"])
        self.assertIn("Build Your own Claude Code", tool_results[1]["content"])


if __name__ == "__main__":
    unittest.main()
