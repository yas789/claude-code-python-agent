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
WORKSPACE_ROOT = Path.cwd()

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
    }
]


def read_file(path):
    file_path = (WORKSPACE_ROOT / path).resolve()
    if not file_path.is_relative_to(WORKSPACE_ROOT):
        raise RuntimeError(f"file is outside workspace: {path}")

    with open(file_path) as file:
        return file.read()


TOOL_FUNCTIONS = {
    "read_file": read_file,
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
    for tool_call in message.tool_calls:
        result = execute_tool_call(tool_call)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )


def main():
    args = parse_args()
    client = create_client()

    messages = [{"role": "user", "content": args.p}]

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    for _ in range(MAX_TOOL_ROUNDS):
        response = create_chat_completion(client, messages)
        message = get_message(response)

        if not message.tool_calls:
            print(message.content)
            return

        append_tool_results(messages, message)

    raise RuntimeError("exceeded maximum tool call rounds")


if __name__ == "__main__":
    main()
