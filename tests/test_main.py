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


if __name__ == "__main__":
    unittest.main()
