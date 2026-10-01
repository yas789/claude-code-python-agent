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

    def test_read_file_ranges_are_optional_positive_integers(self):
        parameters = tool_schema("read_file")["function"]["parameters"]
        self.assertEqual(parameters["required"], ["path"])
        self.assertFalse(parameters["additionalProperties"])
        for name in ("offset", "limit", "max_chars"):
            with self.subTest(argument=name):
                self.assertEqual(parameters["properties"][name]["type"], "integer")
                self.assertEqual(parameters["properties"][name]["minimum"], 1)

    def test_read_file_schema_budgets_match_runtime(self):
        properties = tool_schema("read_file")["function"]["parameters"]["properties"]
        for name, default, maximum in (
            ("limit", main.DEFAULT_READ_LINES, main.MAX_READ_LINES),
            ("max_chars", main.DEFAULT_READ_CHARS, main.MAX_READ_CHARS),
        ):
            self.assertEqual(properties[name]["default"], default)
            self.assertEqual(properties[name]["maximum"], maximum)

    def test_every_advertised_tool_has_a_python_function(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(advertised_tool_names, set(main.TOOL_FUNCTIONS))

    def test_every_python_tool_is_advertised_to_the_llm(self):
        advertised_tool_names = {tool["function"]["name"] for tool in main.TOOLS}

        self.assertLessEqual(set(main.TOOL_FUNCTIONS), advertised_tool_names)


if __name__ == "__main__":
    unittest.main()
