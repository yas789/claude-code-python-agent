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
from app.diagnostics import format_tool_call, summarize_tool_result
from app.errors import ToolError
from app.events import ProgressCallback, ProgressEvent
from app.registry import ToolRegistry, parse_tool_call
from app.schemas import TOOLS as TOOL_SCHEMAS
from app.validation import validate_path, validate_positive_integer, validate_text
from app.workspace import Workspace

BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
TOOLS = TOOL_SCHEMAS


class LocalTools:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def read_file(self, path, offset=1, limit=DEFAULT_READ_LINES, max_chars=DEFAULT_READ_CHARS):
        validate_path(path)
        validate_positive_integer("offset", offset)
        validate_positive_integer("limit", limit, MAX_READ_LINES)
        validate_positive_integer("max_chars", max_chars, MAX_READ_CHARS)

        file_path = self.workspace.resolve_file(path)
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

    def list_files(self, path, offset=1, limit=DEFAULT_LIST_ENTRIES, max_chars=DEFAULT_TOOL_CHARS):
        validate_path(path)
        validate_positive_integer("offset", offset)
        validate_positive_integer("limit", limit, MAX_LIST_ENTRIES)
        validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
        directory_path = self.workspace.resolve_directory(path)
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

    def edit_file(self, path, old_text, new_text):
        validate_path(path)
        validate_text("old_text", old_text)
        validate_text("new_text", new_text, allow_empty=True)
        file_path = self.workspace.resolve_file(path)
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
                "path": str(file_path.relative_to(self.workspace.root)),
                "replacements": 1,
            },
            ensure_ascii=False,
        )

    def create_file(self, path, content):
        validate_path(path)
        validate_text("content", content, allow_empty=True)
        try:
            encoded_content = content.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ToolError("content must be valid UTF-8 text") from error
        file_path = self.workspace.resolve_file(path)
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
                "path": str(file_path.relative_to(self.workspace.root)),
                "chars_written": len(content),
            },
            ensure_ascii=False,
        )

    def search_files(
        self, query, path, limit=DEFAULT_SEARCH_RESULTS, max_chars=DEFAULT_TOOL_CHARS, offset=1
    ):
        validate_path(path)
        validate_text("query", query)
        if len(query) > MAX_SEARCH_QUERY_CHARS:
            raise ToolError(f"query must not exceed {MAX_SEARCH_QUERY_CHARS} characters")
        if "\n" in query or "\r" in query:
            raise ToolError("query must not contain CR or LF")
        validate_positive_integer("limit", limit, MAX_SEARCH_RESULTS)
        validate_positive_integer("max_chars", max_chars, MAX_TOOL_CHARS)
        validate_positive_integer("offset", offset)
        directory_path = self.workspace.resolve_directory(path)
        if not directory_path.is_dir():
            raise ToolError(f"path is not a directory: {path}")

        results = []
        character_count = 0
        truncated = False
        matches = iter_search_matches(self.workspace, directory_path, query, max_chars)
        for match_number, (relative_path, line_number, text, clipped) in enumerate(
            matches, start=1
        ):
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


def create_tool_registry(local_tools: LocalTools) -> ToolRegistry:
    return ToolRegistry(
        TOOL_SCHEMAS,
        [
            local_tools.read_file,
            local_tools.list_files,
            local_tools.edit_file,
            local_tools.create_file,
            local_tools.search_files,
        ],
    )


def iter_search_files(workspace: Workspace, directory_path):
    for directory, dirnames, filenames in os.walk(directory_path, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_SEARCH_DIRS)
        for name in sorted(filenames):
            file_path = Path(directory) / name
            try:
                resolved_path = workspace.resolve_file(str(file_path))
                if resolved_path.is_file():
                    yield file_path.relative_to(workspace.root), resolved_path
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


def iter_search_matches(workspace: Workspace, directory_path, query, snippet_chars):
    for relative_path, file_path in iter_search_files(workspace, directory_path):
        try:
            with open(file_path, encoding="utf-8") as file:
                for line_number, text, clipped in iter_matching_lines(file, query, snippet_chars):
                    yield str(relative_path), line_number, text, clipped
        except UnicodeDecodeError, OSError:
            continue


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
        default=str(Path.cwd()),
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


def create_chat_completion(
    client, messages, model=DEFAULT_MODEL, *, tools: ToolRegistry, temperature=None
):
    options = {} if temperature is None else {"temperature": temperature}
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools.schemas,
        **options,
    )


def get_message(response):
    if not response.choices or len(response.choices) == 0:
        raise RuntimeError("no choices in response")

    return response.choices[0].message


def execute_tool_call(tool_call, *, tools: ToolRegistry):
    return tools.execute(parse_tool_call(tool_call))


def append_tool_results(
    messages,
    message,
    verbose=False,
    *,
    tools: ToolRegistry,
    on_event: ProgressCallback | None = None,
):
    messages.append(message)
    for tool_call in message.tool_calls or []:
        if on_event:
            on_event(ProgressEvent("tool_start", format_tool_call(tool_call)))
        try:
            parsed = parse_tool_call(tool_call)
            if verbose:
                print(format_tool_call(parsed), file=sys.stderr)
            result = tools.execute(parsed)
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
        if on_event:
            on_event(
                ProgressEvent(
                    "tool_end", summarize_tool_result(result), failed=result.startswith("error:")
                )
            )


def run_agent(
    client,
    prompt,
    verbose=False,
    max_tool_rounds=DEFAULT_MAX_TOOL_ROUNDS,
    model=DEFAULT_MODEL,
    *,
    tools: ToolRegistry | None = None,
    messages: list | None = None,
    on_event: ProgressCallback | None = None,
    temperature=None,
):
    if tools is None:
        tools = create_tool_registry(LocalTools(Workspace(Path.cwd())))
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": prompt})

    for _ in range(max_tool_rounds):
        if on_event:
            on_event(ProgressEvent("request"))
        options = {} if temperature is None else {"temperature": temperature}
        response = create_chat_completion(client, messages, model, tools=tools, **options)
        message = get_message(response)
        tool_calls = getattr(message, "tool_calls", None) or []

        if not tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return message.content

        append_tool_results(messages, message, verbose, tools=tools, on_event=on_event)

    raise RuntimeError("exceeded maximum tool call rounds")


def main():
    args = parse_args()
    tools = create_tool_registry(LocalTools(Workspace(args.workspace)))
    client = create_client()

    print(
        run_agent(client, args.prompt, args.verbose, args.max_tool_rounds, args.model, tools=tools)
    )


if __name__ == "__main__":
    main()
