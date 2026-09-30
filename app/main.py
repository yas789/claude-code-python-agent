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
            "description": "List files and directories in the local workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to list.",
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
            "description": "Search text files in the local workspace for a query string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to search.",
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

    with open(file_path) as file:
        lines = file.readlines()
        end = offset - 1 + limit
        selected = []
        character_count = 0
        for line in lines[offset - 1:end]:
            if character_count + len(line) > max_chars:
                if not selected:
                    raise RuntimeError(
                        f"line {offset} exceeds max_chars={max_chars}; "
                        f"increase max_chars up to {MAX_READ_CHARS} or choose another offset"
                    )
                break
            selected.append(line)
            character_count += len(line)
        truncated = offset - 1 + len(selected) < len(lines)

    return json.dumps({
        "content": "".join(selected),
        "start_line": offset,
        "end_line": offset + len(selected) - 1 if selected else None,
        "truncated": truncated,
        "next_offset": offset + len(selected) if truncated else None,
    }, ensure_ascii=False)


def list_files(path):
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise RuntimeError(f"path is not a directory: {path}")

    return "\n".join(sorted(child.name for child in directory_path.iterdir()))


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


def search_files(query, path):
    directory_path = resolve_workspace_path(path, "directory")
    if not directory_path.is_dir():
        raise RuntimeError(f"path is not a directory: {path}")

    results = []
    for file_path in sorted(directory_path.rglob("*")):
        if len(results) >= MAX_SEARCH_RESULTS:
            break
        if not file_path.is_file():
            continue
        if any(part in IGNORED_SEARCH_DIRS for part in file_path.relative_to(directory_path).parts):
            continue

        try:
            lines = file_path.read_text().splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if query in line:
                relative_path = file_path.relative_to(WORKSPACE_ROOT.resolve())
                results.append(f"{relative_path}:{line_number}: {line}")
                if len(results) >= MAX_SEARCH_RESULTS:
                    break

    if not results:
        return "no matches"

    return "\n".join(results)


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
