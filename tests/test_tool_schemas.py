import unittest

from app import main


def tool_schema(name):
    return next(tool for tool in main.TOOLS if tool["function"]["name"] == name)


class ToolSchemaTests(unittest.TestCase):
    def test_read_file_tool_is_advertised_to_the_llm(self):
        tool_names = [tool["function"]["name"] for tool in main.TOOLS]

        self.assertIn("read_file", tool_names)

    def test_read_file_tool_description_mentions_local_workspace(self):
        tool = tool_schema("read_file")

        self.assertIn("local workspace", tool["function"]["description"])

    def test_read_file_tool_requires_path_argument(self):
        tool = tool_schema("read_file")

        self.assertEqual(tool["function"]["parameters"]["required"], ["path"])

    def test_read_file_tool_has_matching_python_function(self):
        self.assertIs(main.TOOL_FUNCTIONS["read_file"], main.read_file)

    def test_every_advertised_tool_has_a_python_function(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(advertised_tool_names, set(main.TOOL_FUNCTIONS))

    def test_every_python_tool_is_advertised_to_the_llm(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(set(main.TOOL_FUNCTIONS), advertised_tool_names)


if __name__ == "__main__":
    unittest.main()
