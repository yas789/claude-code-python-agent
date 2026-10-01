import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from app.config import (
    DEFAULT_LIST_ENTRIES,
    DEFAULT_MAX_TOOL_ROUNDS,
    DEFAULT_MODEL,
    DEFAULT_READ_CHARS,
    DEFAULT_READ_LINES,
    DEFAULT_SEARCH_RESULTS,
    DEFAULT_TOOL_CHARS,
    IGNORED_SEARCH_DIRS,
    MAX_LIST_ENTRIES,
    MAX_READ_CHARS,
    MAX_READ_LINES,
    MAX_SEARCH_QUERY_CHARS,
    MAX_SEARCH_RESULTS,
    MAX_TOOL_CHARS,
    SEARCH_CHUNK_CHARS,
)
from app.errors import ToolError
from app.validation import validate_path, validate_positive_integer, validate_text

BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
WORKSPACE_ROOT = Path.cwd().resolve()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a bounded line range from the local workspace. Returns JSON with content, start_line, end_line, truncated, and next_offset; use next_offset to continue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "The 1-based starting line (default: 1).",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_READ_LINES,
                        "default": DEFAULT_READ_LINES,
                        "description": "Maximum number of lines to read (default: 200; maximum: 2000).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_READ_CHARS,
                        "default": DEFAULT_READ_CHARS,
                        "description": "Content character budget including newlines (default: 16000; maximum: 65536). Complete lines only; increase this budget if a selected line is too long.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List sorted entry names in the local workspace. Returns JSON with entries, truncated, and next_offset; continue with next_offset on an unchanged directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to list.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "The 1-based starting entry.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_LIST_ENTRIES,
                        "default": DEFAULT_LIST_ENTRIES,
                        "description": "Maximum entries to return (default: 100; maximum: 2000).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_CHARS,
                        "default": DEFAULT_TOOL_CHARS,
                        "description": "Entry-name character budget, excluding JSON overhead (default: 16000; maximum: 65536).",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace one nonempty exact text match in a UTF-8 file in the local workspace. Returns a JSON receipt with status, resolved workspace-relative path, and replacements. An empty new_text deletes the match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to edit.",
                    },
                    "old_text": {
                        "type": "string",
                        "minLength": 1,
                        "description": "The nonempty exact existing text to replace; must occur once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new UTF-8 file in the local workspace without overwriting existing files. Empty content is allowed. Returns a JSON receipt with status, resolved workspace-relative path, and chars_written; content is written in full.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to create.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the new file.",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search UTF-8 files in the local workspace for a case-sensitive substring. Returns JSON results with path, line, text, and text_truncated, plus truncated and next_offset. Continue with next_offset and the same query/path on an unchanged tree. Clipped text is a line prefix and may omit the query; use read_file at that line for more detail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_SEARCH_QUERY_CHARS,
                        "pattern": "^[^\r\n]+$",
                        "description": "Nonempty, case-sensitive substring without CR/LF (maximum: 4096 characters).",
                    },
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to search.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "The 1-based matching-line offset, not a file line number. Continuation rescans the unchanged tree.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_RESULTS,
                        "default": DEFAULT_SEARCH_RESULTS,
                        "description": "Maximum matching lines (default: 20; maximum: 200).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_CHARS,
                        "default": DEFAULT_TOOL_CHARS,
                        "description": "Total snippet-character budget excluding metadata and JSON overhead (default: 16000; maximum: 65536).",
                    },
                },
                "required": ["query", "path"],
                "additionalProperties": False,
            },
        },
    },
]


def resolve_workspace_path(path, path_type):
    workspace_root = WORKSPACE_ROOT.resolve()
    resolved_path = (workspace_root / path).resolve()
    if not resolved_path.is_relative_to(workspace_root):
        raise ToolError(f"{path_type} is outside workspace: {path}")

    return resolved_path


def read_file(path, offset=1, limit=DEFAULT_READ_LINES, max_chars=DEFAULT_READ_CHARS):
    validate_path(path)
    validate_positive_integer("offset", offset)
    validate_positive_integer("limit", limit, MAX_READ_LINES)
    validate_positive_integer("max_chars", max_chars, MAX_READ_CHARS)

    file_path = resolve_workspace_path(path, "file")
    if not file_path.is_file():
        raise ToolError(f"path is not a file: {path}")

    with open(file_path, encoding="utf-8") as file:
        for _ in range(offset - 1):
            chunk = file.readline(max_chars + 1)
            if not chunk:
                break
            while chunk and not chunk.endswith("\n"):
                chunk = file.readline(max_chars + 1)
        selected = []
        character_count = 0
        truncated = False
        for _ in range(limit):
            line = file.readline(max_chars - character_count + 1)
            if not line:
                break
            if character_count + len(line) > max_chars:
                if not selected:
                    raise ToolError(
                        f"line {offset} exceeds max_chars={max_chars}; "
                        f"increase max_chars up to {MAX_READ_CHARS} or choose another offset"
                    )
                truncated = True
                break
            selected.append(line)
            character_count += len(line)
        else:
            truncated = bool(file.read(1))

    return json.dumps(
        {
            "content": "".join(selected),
            "start_line": offset,
            "end_line": offset + len(selected) - 1 if selected else None,
            "truncated": truncated,
            "next_offset": offset + len(selected) if truncated else None,
        },
        ensure_ascii=False,
    )


def list_files(path, offset=1, limit=DEFAULT_LIST_ENTRIES, max_chars=DEFAULT_TOOL_CHARS):
    validate_path(path)
    validate_positive_integer("offset", offset)
    validate_positive_integer("limit", limit, MAX_LIST_ENTRIES)
    validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise ToolError(f"path is not a directory: {path}")

    names = sorted(child.name for child in directory_path.iterdir())
    entries = []
    character_count = 0
    for name in names[offset - 1 : offset - 1 + limit]:
        if character_count + len(name) > max_chars:
            if not entries:
                raise ToolError("entry name exceeds max_chars; increase max_chars")
            break
        entries.append(name)
        character_count += len(name)
    truncated = offset - 1 + len(entries) < len(names)
    return json.dumps(
        {
            "entries": entries,
            "truncated": truncated,
            "next_offset": offset + len(entries) if truncated else None,
        },
        ensure_ascii=False,
    )


def edit_file(path, old_text, new_text):
    validate_path(path)
    validate_text("old_text", old_text)
    validate_text("new_text", new_text, allow_empty=True)
    file_path = resolve_workspace_path(path, "file")
    if not file_path.is_file():
        raise ToolError(f"path is not a file: {path}")

    content = file_path.read_text(encoding="utf-8")
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise ToolError("old_text not found")
    if occurrences > 1:
        raise ToolError("old_text appears multiple times")

    file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
    return json.dumps(
        {
            "status": "updated",
            "path": str(file_path.relative_to(WORKSPACE_ROOT.resolve())),
            "replacements": 1,
        },
        ensure_ascii=False,
    )


def create_file(path, content):
    validate_path(path)
    validate_text("content", content, allow_empty=True)
    try:
        encoded_content = content.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ToolError("content must be valid UTF-8 text") from error
    file_path = resolve_workspace_path(path, "file")
    if file_path.exists():
        raise ToolError(f"file already exists: {path}")
    if not file_path.parent.is_dir():
        raise ToolError(f"parent directory does not exist: {path}")

    try:
        with open(file_path, "xb") as file:
            file.write(encoded_content)
    except FileExistsError as error:
        raise ToolError(f"file already exists: {path}") from error
    return json.dumps(
        {
            "status": "created",
            "path": str(file_path.relative_to(WORKSPACE_ROOT.resolve())),
            "chars_written": len(content),
        },
        ensure_ascii=False,
    )


def iter_search_files(directory_path):
    workspace_root = WORKSPACE_ROOT.resolve()
    for directory, dirnames, filenames in os.walk(directory_path, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_SEARCH_DIRS)
        for name in sorted(filenames):
            file_path = Path(directory) / name
            try:
                resolved_path = resolve_workspace_path(str(file_path), "file")
                if resolved_path.is_file():
                    yield file_path.relative_to(workspace_root), resolved_path
            except ToolError, OSError:
                continue


def iter_matching_lines(file, query, snippet_chars):
    line_number = 0
    while True:
        chunk = file.readline(SEARCH_CHUNK_CHARS)
        if not chunk:
            return
        line_number += 1
        snippet = ""
        tail = ""
        matched = False
        while chunk:
            complete = chunk.endswith("\n")
            text = chunk[:-1] if complete else chunk
            combined = tail + text
            matched = matched or query in combined
            tail = combined[-(len(query) - 1) :] if len(query) > 1 else ""
            snippet = (snippet + text)[: snippet_chars + 1]
            if complete:
                break
            chunk = file.readline(SEARCH_CHUNK_CHARS)
        if matched:
            yield line_number, snippet[:snippet_chars], len(snippet) > snippet_chars


def iter_search_matches(directory_path, query, snippet_chars):
    for relative_path, file_path in iter_search_files(directory_path):
        try:
            with open(file_path, encoding="utf-8") as file:
                for line_number, text, clipped in iter_matching_lines(file, query, snippet_chars):
                    yield str(relative_path), line_number, text, clipped
        except UnicodeDecodeError, OSError:
            continue


def search_files(query, path, limit=DEFAULT_SEARCH_RESULTS, max_chars=DEFAULT_TOOL_CHARS, offset=1):
    validate_path(path)
    validate_text("query", query)
    if len(query) > MAX_SEARCH_QUERY_CHARS:
        raise ToolError(f"query must not exceed {MAX_SEARCH_QUERY_CHARS} characters")
    if "\n" in query or "\r" in query:
        raise ToolError("query must not contain CR or LF")
    validate_positive_integer("limit", limit, MAX_SEARCH_RESULTS)
    validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
    validate_positive_integer("offset", offset)
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise ToolError(f"path is not a directory: {path}")

    results = []
    character_count = 0
    truncated = False
    matches = iter_search_matches(directory_path, query, max_chars)
    for match_number, (relative_path, line_number, text, clipped) in enumerate(matches, start=1):
        if match_number < offset:
            continue
        if len(results) >= limit or character_count >= max_chars:
            truncated = True
            break
        snippet = text[: max_chars - character_count]
        results.append(
            {
                "path": relative_path,
                "line": line_number,
                "text": snippet,
                "text_truncated": clipped or len(snippet) < len(text),
            }
        )
        character_count += len(snippet)

    return json.dumps(
        {
            "results": results,
            "truncated": truncated,
            "next_offset": offset + len(results) if truncated else None,
        },
        ensure_ascii=False,
    )


TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
    "create_file": create_file,
    "search_files": search_files,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a local coding agent with OpenAI-compatible tool calls."
    )
    parser.add_argument("-p", "--prompt", required=True, help="Prompt to send to the agent.")
    parser.add_argument("--verbose", action="store_true", help="Print tool activity to stderr.")
    parser.add_argument(
        "--quiet", action="store_true", help="Reserve minimal output mode for scripts."
    )
    parser.add_argument(
        "--max-tool-rounds",
        type=int,
        default=DEFAULT_MAX_TOOL_ROUNDS,
        help="Maximum number of tool-call rounds before stopping.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model name to use.")
    parser.add_argument(
        "--workspace",
        default=str(WORKSPACE_ROOT),
        help="Workspace directory the agent can inspect and edit.",
    )
    args = parser.parse_args()

    if args.verbose and args.quiet:
        parser.error("--verbose and --quiet cannot be used together")
    if args.max_tool_rounds < 1:
        parser.error("--max-tool-rounds must be at least 1")

    args.workspace = Path(args.workspace).resolve()
    if not args.workspace.is_dir():
        parser.error("--workspace must be an existing directory")

    return args


def create_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    return OpenAI(api_key=api_key, base_url=BASE_URL)


def create_chat_completion(client, messages, model=DEFAULT_MODEL):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
    )


def get_message(response):
    if not response.choices or len(response.choices) == 0:
        raise RuntimeError("no choices in response")

    return response.choices[0].message


def execute_tool_call(tool_call):
    tool_name = tool_call.function.name
    if tool_name not in TOOL_FUNCTIONS:
        raise RuntimeError(f"unknown tool: {tool_name}")

    arguments = json.loads(tool_call.function.arguments)
    return TOOL_FUNCTIONS[tool_name](**arguments)


def summarize_tool_result(result):
    if result.startswith("error:"):
        return result

    line_count = len(result.splitlines())
    if line_count > 1:
        return f"ok ({line_count} lines)"

    return "ok"


def format_tool_call(tool_call):
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return f"Using {tool_call.function.name} with invalid JSON arguments"

    formatted_arguments = " ".join(f"{name}={value}" for name, value in sorted(arguments.items()))
    if not formatted_arguments:
        return f"Using {tool_call.function.name}"

    return f"Using {tool_call.function.name} {formatted_arguments}"


def append_tool_results(messages, message, verbose=False):
    messages.append(message)
    for tool_call in message.tool_calls or []:
        if verbose:
            print(format_tool_call(tool_call), file=sys.stderr)

        try:
            result = execute_tool_call(tool_call)
        except Exception as error:
            result = f"error: {error}"

        if verbose:
            print(f"Tool result: {summarize_tool_result(result)}", file=sys.stderr)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )


def run_agent(
    client, prompt, verbose=False, max_tool_rounds=DEFAULT_MAX_TOOL_ROUNDS, model=DEFAULT_MODEL
):
    messages = [{"role": "user", "content": prompt}]

    for _ in range(max_tool_rounds):
        response = create_chat_completion(client, messages, model)
        message = get_message(response)
        tool_calls = getattr(message, "tool_calls", None) or []

        if not tool_calls:
            return message.content

        append_tool_results(messages, message, verbose)

    raise RuntimeError("exceeded maximum tool call rounds")


def main():
    global WORKSPACE_ROOT

    args = parse_args()
    WORKSPACE_ROOT = args.workspace
    client = create_client()

    print(run_agent(client, args.prompt, args.verbose, args.max_tool_rounds, args.model))


if __name__ == "__main__":
    main()
