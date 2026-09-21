import argparse
import json
import os
from pathlib import Path
import sys

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
MODEL = "anthropic/claude-haiku-4.5"
MAX_TOOL_ROUNDS = 10
WORKSPACE_ROOT = Path.cwd().resolve()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the local workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to read.",
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
    }
]


def resolve_workspace_path(path, path_type):
    workspace_root = WORKSPACE_ROOT.resolve()
    resolved_path = (workspace_root / path).resolve()
    if not resolved_path.is_relative_to(workspace_root):
        raise RuntimeError(f"{path_type} is outside workspace: {path}")

    return resolved_path


def read_file(path):
    file_path = resolve_workspace_path(path, "file")

    with open(file_path) as file:
        return file.read()


def list_files(path):
    directory_path = resolve_workspace_path(path, "directory")

    return "\n".join(sorted(child.name for child in directory_path.iterdir()))


def edit_file(path, old_text, new_text):
    file_path = resolve_workspace_path(path, "file")

    content = file_path.read_text()
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise RuntimeError("old_text not found")
    if occurrences > 1:
        raise RuntimeError("old_text appears multiple times")

    file_path.write_text(content.replace(old_text, new_text))
    return f"updated {path}"


TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", required=True)
    return parser.parse_args()


def create_client():
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def create_chat_completion(client, messages):
    return client.chat.completions.create(
        model=MODEL,
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


def append_tool_results(messages, message):
    messages.append(message)
    for tool_call in message.tool_calls or []:
        result = execute_tool_call(tool_call)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )


def run_agent(client, prompt):
    messages = [{"role": "user", "content": prompt}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = create_chat_completion(client, messages)
        message = get_message(response)
        tool_calls = getattr(message, "tool_calls", None) or []

        if not tool_calls:
            return message.content

        append_tool_results(messages, message)

    raise RuntimeError("exceeded maximum tool call rounds")


def main():
    args = parse_args()
    client = create_client()

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    print(run_agent(client, args.p))


if __name__ == "__main__":
    main()
