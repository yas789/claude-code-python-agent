import sys
import unittest
from types import SimpleNamespace

sys.modules["openai"] = SimpleNamespace(OpenAI=object)

from app import main


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


if __name__ == "__main__":
    unittest.main()
