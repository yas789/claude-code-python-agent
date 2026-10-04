import unittest
from types import SimpleNamespace

from app.errors import ToolError
from app.registry import ParsedToolCall, ToolRegistry, parse_tool_call
from tests.helpers import tool_call


class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def example(path, limit=3):
            self.calls.append((path, limit))
            return f"{path}:{limit}"

        self.function = example
        self.schema = {"type": "function", "function": {"name": "example"}}
        self.registry = ToolRegistry([self.schema], [example])

    def test_dispatch_preserves_defaults_and_named_arguments(self):
        for arguments, expected in (({"path": "a"}, "a:3"), ({"path": "b", "limit": 2}, "b:2")):
            with self.subTest(arguments=arguments):
                self.assertEqual(
                    self.registry.execute(ParsedToolCall("example", arguments)), expected
                )
        self.assertEqual(self.calls, [("a", 3), ("b", 2)])

    def test_missing_and_unknown_arguments_fail_before_execution(self):
        for arguments in ({}, {"path": "a", "extra": True}):
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ToolError, "invalid arguments for example"):
                    self.registry.execute(ParsedToolCall("example", arguments))
        self.assertEqual(self.calls, [])

    def test_unknown_tool_is_rejected(self):
        with self.assertRaisesRegex(ToolError, "unknown tool: missing"):
            self.registry.execute(ParsedToolCall("missing", {}))
        self.assertEqual(self.calls, [])

    def test_registry_rejects_duplicate_names(self):
        for schemas, functions, error in (
            ([self.schema, self.schema], [self.function], "duplicate schema name"),
            ([self.schema], [self.function, self.function], "duplicate function name"),
        ):
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    ToolRegistry(schemas, functions)

    def test_registry_rejects_missing_bindings_in_both_directions(self):
        for schemas, functions in (([self.schema], []), ([], [self.function])):
            with self.subTest(schemas=schemas):
                with self.assertRaisesRegex(ValueError, "schema/function names mismatch"):
                    ToolRegistry(schemas, functions)

    def test_parse_valid_named_arguments(self):
        self.assertEqual(
            parse_tool_call(tool_call("id", "example", '{"path": "a"}')),
            ParsedToolCall("example", {"path": "a"}),
        )

    def test_parse_rejects_invalid_json_and_non_objects(self):
        for arguments in ("{", None, "[]", "null", '"text"', "1", "true"):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ToolError):
                    parse_tool_call(tool_call("id", "example", arguments))

    def test_parse_rejects_missing_or_invalid_names(self):
        for rawcall in (
            SimpleNamespace(),
            SimpleNamespace(function=SimpleNamespace(arguments="{}")),
            *(tool_call("id", name, "{}") for name in (None, "", " ", 1)),
        ):
            with self.subTest(rawcall=rawcall):
                with self.assertRaisesRegex(ToolError, "tool name must be a nonempty string"):
                    parse_tool_call(rawcall)
