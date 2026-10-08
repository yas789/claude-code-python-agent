import unittest

from app import main


class ToolContractTests(unittest.TestCase):
    def test_edit_file_tool_requires_precise_replacement_arguments(self):
        edit_file_tool = next(
            tool for tool in main.TOOLS if tool["function"]["name"] == "edit_file"
        )

        self.assertEqual(
            edit_file_tool["function"]["parameters"]["required"],
            ["path", "old_text", "new_text"],
        )

    def test_edit_file_tool_does_not_allow_extra_arguments(self):
        edit_file_tool = next(
            tool for tool in main.TOOLS if tool["function"]["name"] == "edit_file"
        )

        self.assertFalse(edit_file_tool["function"]["parameters"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
