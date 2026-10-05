"""Installable mlab command."""

import argparse
from pathlib import Path

from app.chat import chat
from app.config import DEFAULT_MAX_TOOL_ROUNDS
from app.input import Input
from app.main import LocalTools, create_tool_registry, run_agent
from app.session import Session
from app.settings import Settings
from app.terminal import Terminal
from app.workspace import Workspace


def parse_args(argv=None):
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="mlab — your local coding companion")
    parser.add_argument("-p", "--prompt", help="Run one prompt and exit.")
    parser.add_argument("--model", default=settings.model, help="Model name to use.")
    parser.add_argument("--base-url", default=settings.base_url, help="OpenAI-compatible API URL.")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="Project directory.")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--verbose", action="store_true", help="Show tool activity.")
    output.add_argument("--quiet", action="store_true", help="Print only the final answer.")
    parser.add_argument("--max-tool-rounds", type=int, default=DEFAULT_MAX_TOOL_ROUNDS)
    args = parser.parse_args(argv)
    args.workspace = Path(args.workspace).expanduser().resolve()
    if not args.workspace.is_dir():
        parser.error("--workspace must be an existing directory")
    if args.max_tool_rounds < 1:
        parser.error("--max-tool-rounds must be at least 1")
    if not args.model.strip():
        parser.error("--model must not be empty")
    if args.prompt is not None and not args.prompt.strip():
        parser.error("--prompt must not be empty")
    return args


def main():
    args = parse_args()
    settings = Settings(args.base_url, Settings.from_env().api_key, args.model)
    tools = create_tool_registry(LocalTools(Workspace(args.workspace)))
    with settings.create_client() as client:
        if args.prompt is None:
            terminal = Terminal()
            terminal.welcome(args.workspace, args.model, args.base_url)
            return chat(Session(client, tools, args.model, args.max_tool_rounds), terminal, Input())
        print(
            run_agent(
                client, args.prompt, args.verbose, args.max_tool_rounds, args.model, tools=tools
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
