import argparse
import json
import os
from pathlib import Path
import sys

from openai import OpenAI

BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
MODEL = "anthropic/claude-haiku-4.5"
MAX_TOOL_ROUNDS = 10
WORKSPACE_ROOT = Path.cwd().resolve()
IGNORED_SEARCH_DIRS = {".git", ".venv", "__pycache__"}
MAX_SEARCH_RESULTS = 20
DEFAULT_READ_LINES = 200
MAX_READ_LINES = 2000
DEFAULT_READ_CHARS = 16000
MAX_READ_CHARS = 65536
DEFAULT_LIST_ENTRIES = 100
MAX_LIST_ENTRIES = 2000
DEFAULT_TOOL_CHARS = 16000
MAX_TOOL_CHARS = 65536
SEARCH_RESULT_CEILING = 200
MAX_SEARCH_QUERY = 4096
SEARCH_CHUNK_CHARS = 4096

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
                        "type": "integer", "minimum": 1, "default": 1,
                        "description": "The 1-based starting entry.",
                    },
                    "limit": {
                        "type": "integer", "minimum": 1,
                        "maximum": MAX_LIST_ENTRIES, "default": DEFAULT_LIST_ENTRIES,
                        "description": "Maximum entries to return (default: 100; maximum: 2000).",
                    },
                    "max_chars": {
                        "type": "integer", "minimum": 1,
                        "maximum": MAX_TOOL_CHARS, "default": DEFAULT_TOOL_CHARS,
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
            "description": "Replace exact text in a file in the local workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to edit.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact existing text to replace.",
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
            "description": "Create a new file in the local workspace without overwriting existing files.",
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
            "description": "Search UTF-8 files in the local workspace for a case-sensitive substring. Returns JSON results with path, line, text, and text_truncated; page truncated means more matching lines remain. Clipped text is a line prefix and may omit the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_SEARCH_QUERY,
                        "pattern": "^[^\r\n]+$",
                        "description": "Nonempty, case-sensitive substring without CR/LF (maximum: 4096 characters).",
                    },
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to search.",
                    },
                    "limit": {
                        "type": "integer", "minimum": 1,
                        "maximum": SEARCH_RESULT_CEILING, "default": MAX_SEARCH_RESULTS,
                        "description": "Maximum matching lines (default: 20; maximum: 200).",
                    },
                    "max_chars": {
                        "type": "integer", "minimum": 1,
                        "maximum": MAX_TOOL_CHARS, "default": DEFAULT_TOOL_CHARS,
                        "description": "Total snippet-character budget excluding metadata and JSON overhead (default: 16000; maximum: 65536).",
                    },
                },
                "required": ["query", "path"],
                "additionalProperties": False,
            },
        },
    }
]


def resolve_workspace_path(path, path_type):
    workspace_root = WORKSPACE_ROOT.resolve()
    resolved_path = (workspace_root / path).resolve()
    if not resolved_path.is_relative_to(workspace_root):
        raise RuntimeError(f"{path_type} is outside workspace: {path}")

    return resolved_path


def read_file(path, offset=1, limit=DEFAULT_READ_LINES, max_chars=DEFAULT_READ_CHARS):
    if type(offset) is not int or offset < 1:
        raise RuntimeError("offset must be a positive integer")
    if type(limit) is not int or limit < 1:
        raise RuntimeError("limit must be a positive integer")
    if limit > MAX_READ_LINES:
        raise RuntimeError(f"limit must not exceed {MAX_READ_LINES}")
    if type(max_chars) is not int or max_chars < 1:
        raise RuntimeError("max_chars must be a positive integer")
    if max_chars > MAX_READ_CHARS:
        raise RuntimeError(f"max_chars must not exceed {MAX_READ_CHARS}")

    file_path = resolve_workspace_path(path, "file")
    if not file_path.is_file():
        raise RuntimeError(f"path is not a file: {path}")

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
                    raise RuntimeError(
                        f"line {offset} exceeds max_chars={max_chars}; "
                        f"increase max_chars up to {MAX_READ_CHARS} or choose another offset"
                    )
                truncated = True
                break
            selected.append(line)
            character_count += len(line)
        else:
            truncated = bool(file.read(1))

    return json.dumps({
        "content": "".join(selected),
        "start_line": offset,
        "end_line": offset + len(selected) - 1 if selected else None,
        "truncated": truncated,
        "next_offset": offset + len(selected) if truncated else None,
    }, ensure_ascii=False)


def validate_positive_integer(name, value, maximum=None):
    if type(value) is not int or value < 1:
        raise RuntimeError(f"{name} must be a positive integer")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must not exceed {maximum}")


def validate_text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise RuntimeError(f"{name} must be a string")
    if not allow_empty and not value:
        raise RuntimeError(f"{name} must not be empty")


def validate_path(path):
    validate_text("path", path)
    if "\0" in path:
        raise RuntimeError("path must not contain null characters")


def list_files(path, offset=1, limit=DEFAULT_LIST_ENTRIES, max_chars=DEFAULT_TOOL_CHARS):
    validate_path(path)
    validate_positive_integer("offset", offset)
    validate_positive_integer("limit", limit, MAX_LIST_ENTRIES)
    validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise RuntimeError(f"path is not a directory: {path}")

    names = sorted(child.name for child in directory_path.iterdir())
    entries = []
    character_count = 0
    for name in names[offset - 1:offset - 1 + limit]:
        if character_count + len(name) > max_chars:
            if not entries:
                raise RuntimeError("entry name exceeds max_chars; increase max_chars")
            break
        entries.append(name)
        character_count += len(name)
    truncated = offset - 1 + len(entries) < len(names)
    return json.dumps({
        "entries": entries,
        "truncated": truncated,
        "next_offset": offset + len(entries) if truncated else None,
    }, ensure_ascii=False)


def edit_file(path, old_text, new_text):
    file_path = resolve_workspace_path(path, "file")
    if not file_path.is_file():
        raise RuntimeError(f"path is not a file: {path}")

    content = file_path.read_text()
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise RuntimeError("old_text not found")
    if occurrences > 1:
        raise RuntimeError("old_text appears multiple times")

    file_path.write_text(content.replace(old_text, new_text, 1))
    return f"updated {path}"


def create_file(path, content):
    file_path = resolve_workspace_path(path, "file")
    if file_path.exists():
        raise RuntimeError(f"file already exists: {path}")
    if not file_path.parent.is_dir():
        raise RuntimeError(f"parent directory does not exist: {path}")

    file_path.write_text(content)
    return f"created {path}"


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
            except (RuntimeError, OSError):
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
            tail = combined[-(len(query) - 1):] if len(query) > 1 else ""
            snippet = (snippet + text)[:snippet_chars + 1]
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
        except (UnicodeDecodeError, OSError):
            continue


def search_files(query, path, limit=MAX_SEARCH_RESULTS, max_chars=DEFAULT_TOOL_CHARS):
    validate_path(path)
    validate_text("query", query)
    if len(query) > MAX_SEARCH_QUERY:
        raise RuntimeError(f"query must not exceed {MAX_SEARCH_QUERY} characters")
    if "\n" in query or "\r" in query:
        raise RuntimeError("query must not contain CR or LF")
    validate_positive_integer("limit", limit, SEARCH_RESULT_CEILING)
    validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise RuntimeError(f"path is not a directory: {path}")

    results = []
    character_count = 0
    truncated = False
    for relative_path, line_number, text, clipped in iter_search_matches(directory_path, query, max_chars):
        if len(results) >= limit or character_count >= max_chars:
            truncated = True
            break
        snippet = text[:max_chars - character_count]
        results.append({
            "path": relative_path,
            "line": line_number,
            "text": snippet,
            "text_truncated": clipped or len(snippet) < len(text),
        })
        character_count += len(snippet)

    return json.dumps({"results": results, "truncated": truncated}, ensure_ascii=False)


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
    parser.add_argument("--quiet", action="store_true", help="Reserve minimal output mode for scripts.")
    parser.add_argument(
        "--max-tool-rounds",
        type=int,
        default=MAX_TOOL_ROUNDS,
        help="Maximum number of tool-call rounds before stopping.",
    )
    parser.add_argument("--model", default=MODEL, help="OpenRouter model name to use.")
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


def create_chat_completion(client, messages, model=MODEL):
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

    formatted_arguments = " ".join(
        f"{name}={value}" for name, value in sorted(arguments.items())
    )
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


def run_agent(client, prompt, verbose=False, max_tool_rounds=MAX_TOOL_ROUNDS, model=MODEL):
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
