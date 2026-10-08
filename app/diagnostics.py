import json
from typing import Any

from app.errors import ToolError
from app.registry import ParsedToolCall, parse_tool_call

MAX_VALUE_CHARS = 100
MAX_SUMMARY_CHARS = 500
CONTENT_FIELDS = {"old_text", "new_text", "content"}


def clipped(value: str, limit: int = MAX_VALUE_CHARS) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def format_tool_call(tool_call: Any) -> str:
    if not isinstance(tool_call, ParsedToolCall):
        try:
            tool_call = parse_tool_call(tool_call)
        except ToolError:
            name = getattr(getattr(tool_call, "function", None), "name", "unknown tool")
            return clipped(
                f"Using {clipped(str(name))} with invalid JSON arguments", MAX_SUMMARY_CHARS
            )

    parts = []
    for name, value in sorted(tool_call.arguments.items()):
        if name in CONTENT_FIELDS:
            summary = f"{len(value)} chars" if isinstance(value, str) else type(value).__name__
        elif isinstance(value, str):
            summary = clipped(value).replace("\n", "\\n").replace("\r", "\\r")
        elif isinstance(value, (dict, list)):
            summary = f"{len(value)} items"
        else:
            summary = clipped(str(value))
        parts.append(f"{clipped(name)}={summary}")
        if sum(map(len, parts)) >= MAX_SUMMARY_CHARS:
            break
    return clipped(" ".join([f"Using {clipped(tool_call.name)}", *parts]), MAX_SUMMARY_CHARS)


def summarize_tool_result(result: str) -> str:
    if result.startswith("error:"):
        return clipped(result, MAX_SUMMARY_CHARS)
    try:
        data = json.loads(result)
    except json.JSONDecodeError, TypeError:
        data = None
    if isinstance(data, dict):
        parts = []
        for key in ("entries", "results"):
            if isinstance(data.get(key), list):
                parts.append(f"{len(data[key])} {key}")
        if "start_line" in data and "end_line" in data:
            parts.append(
                f"lines {clipped(str(data['start_line']))}-{clipped(str(data['end_line']))}"
            )
        if isinstance(data.get("status"), str):
            parts.append(clipped(data["status"]))
        if "truncated" in data:
            parts.append(f"truncated={bool(data['truncated'])}")
        if parts:
            return clipped(f"ok ({', '.join(parts)})", MAX_SUMMARY_CHARS)
    line_count = len(result.splitlines())
    return f"ok ({line_count} lines)" if line_count > 1 else "ok"
