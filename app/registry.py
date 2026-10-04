import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from inspect import signature
from typing import Any

from app.errors import ToolError


@dataclass(frozen=True)
class ParsedToolCall:
    name: str
    arguments: dict[str, Any]


def parse_tool_call(rawcall: Any) -> ParsedToolCall:
    function = getattr(rawcall, "function", None)
    name = getattr(function, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise ToolError("tool name must be a nonempty string; provide a registered function name")
    try:
        arguments = json.loads(getattr(function, "arguments", None))
    except (json.JSONDecodeError, TypeError) as error:
        raise ToolError(
            f"invalid JSON arguments for {name}; provide a valid JSON object"
        ) from error
    if not isinstance(arguments, dict):
        raise ToolError(f"arguments for {name} must be a JSON object with named parameters")
    return ParsedToolCall(name, arguments)


class ToolRegistry:
    def __init__(
        self, schemas: Iterable[dict[str, Any]], functions: Iterable[Callable[..., str]]
    ) -> None:
        schema_map = {}
        for schema in schemas:
            name = schema["function"]["name"]
            if name in schema_map:
                raise ValueError(f"duplicate schema name: {name}")
            schema_map[name] = schema
        function_map = {}
        for function in functions:
            name = function.__name__
            if name in function_map:
                raise ValueError(f"duplicate function name: {name}")
            function_map[name] = function
        if schema_map.keys() != function_map.keys():
            raise ValueError(
                "schema/function names mismatch: "
                f"missing functions={sorted(schema_map.keys() - function_map.keys())}, "
                f"missing schemas={sorted(function_map.keys() - schema_map.keys())}"
            )
        self._bindings = {name: (schema, function_map[name]) for name, schema in schema_map.items()}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [schema for schema, _ in self._bindings.values()]

    @property
    def functions(self) -> dict[str, Callable[..., str]]:
        return {name: function for name, (_, function) in self._bindings.items()}

    def execute(self, parsed: ParsedToolCall) -> str:
        if parsed.name not in self._bindings:
            raise ToolError(f"unknown tool: {parsed.name}")
        _, function = self._bindings[parsed.name]
        try:
            signature(function).bind(**parsed.arguments)
        except TypeError as error:
            raise ToolError(
                f"invalid arguments for {parsed.name}: {error}; "
                "provide the required parameters and remove unknown parameters"
            ) from error
        return function(**parsed.arguments)
