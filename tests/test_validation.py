import unittest
from unittest.mock import patch

from app import main
from app.errors import AgentError, ConfigurationError, ToolError
from app.validation import validate_path, validate_positive_integer, validate_text
from app.workspace import Workspace
from tests import helpers


class PrimitiveValidationTests(unittest.TestCase):
    def test_positive_integer_rejects_bool_and_non_integer_values(self):
        validate_positive_integer("limit", 1)
        for value in (True, False, 1.0, "1", None, 0, -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ToolError, "^limit must be a positive integer$"):
                    validate_positive_integer("limit", value)

    def test_integer_maximum_is_inclusive_and_optional(self):
        validate_positive_integer("limit", 3, maximum=3)
        validate_positive_integer("limit", 4)
        with self.assertRaisesRegex(ToolError, "^limit must not exceed 3$"):
            validate_positive_integer("limit", 4, maximum=3)

    def test_text_distinguishes_wrong_type_from_empty_text(self):
        with self.assertRaisesRegex(ToolError, "^content must be a string$"):
            validate_text("content", None, allow_empty=True)
        with self.assertRaisesRegex(ToolError, "^content must not be empty$"):
            validate_text("content", "")
        validate_text("content", "", allow_empty=True)
        validate_text("content", " ")
        validate_text("content", "🙂")

    def test_path_validation_is_lexical_not_a_filesystem_check(self):
        validate_path("missing/file.txt")
        validate_path("../outside.txt")
        for value, message in (
            (None, "path must be a string"),
            ("", "path must not be empty"),
            ("bad\0path", "path must not contain null characters"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ToolError, f"^{message}$"):
                    validate_path(value)

    def test_error_categories_are_distinct_runtime_errors(self):
        for error_type in (ToolError, AgentError, ConfigurationError):
            with self.subTest(error_type=error_type):
                self.assertIsInstance(error_type("failure"), RuntimeError)
        self.assertFalse(issubclass(AgentError, ToolError))
        self.assertFalse(issubclass(ConfigurationError, ToolError))


class ToolErrorTests(helpers.WorkspaceTestCase):
    def test_workspace_escape_raises_tool_error(self):
        with self.assertRaisesRegex(ToolError, "^file is outside workspace: ../outside.txt$"):
            self.tools.workspace.resolve_file("../outside.txt")

    def test_tool_failures_use_tool_error(self):
        cases = (
            (self.tools.read_file, ("missing.txt",), "path is not a file"),
            (self.tools.list_files, ("missing",), "path is not a directory"),
            (self.tools.edit_file, ("missing.txt", "old", "new"), "path is not a file"),
            (
                self.tools.create_file,
                ("missing/new.txt", "content"),
                "parent directory does not exist",
            ),
            (self.tools.search_files, ("\n", "."), "query must not contain CR or LF"),
        )
        for tool, arguments, message in cases:
            with self.subTest(tool=tool.__name__):
                with self.assertRaisesRegex(ToolError, message):
                    tool(*arguments)

    def test_search_skips_expected_failures_but_propagates_unexpected_runtime_errors(self):
        (self.root / "example.txt").write_text("example", encoding="utf-8")
        for error in (ToolError("outside workspace"), OSError("unreadable")):
            with self.subTest(error=type(error)):
                with patch.object(Workspace, "resolve_file", side_effect=error):
                    self.assertEqual(
                        list(main.iter_search_files(self.tools.workspace, self.root)), []
                    )
        with patch.object(
            Workspace, "resolve_file", side_effect=RuntimeError("unexpected failure")
        ):
            with self.assertRaisesRegex(RuntimeError, "^unexpected failure$"):
                list(main.iter_search_files(self.tools.workspace, self.root))
