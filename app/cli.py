"""Installable mlab command."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from openai import APIError
from rich.console import Console

from app.chat import chat
from app.config import DEFAULT_MAX_TOOL_ROUNDS
from app.failures import describe_failure
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
    try:
        endpoint = urlparse(args.base_url)
        valid_url = endpoint.scheme in ("http", "https") and endpoint.hostname
        endpoint.port
    except ValueError:
        valid_url = False
    if not valid_url:
        parser.error("--base-url must be a valid HTTP or HTTPS URL")
    if args.prompt is not None and not args.prompt.strip():
        parser.error("--prompt must not be empty")
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.prompt is None and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        print('Interactive mlab needs a terminal. Use: mlab --prompt "your task"', file=sys.stderr)
        return 2
    settings = Settings(args.base_url, Settings.from_env().api_key, args.model)
    tools = create_tool_registry(LocalTools(Workspace(args.workspace)))
    try:
        with settings.create_client() as client:
            if args.prompt is None:
                terminal = Terminal(quiet=args.quiet)
                terminal.welcome(args.workspace, args.model, args.base_url)
                return chat(
                    Session(client, tools, args.model, args.max_tool_rounds),
                    terminal,
                    Input(),
                    base_url=args.base_url,
                )
            if sys.stdout.isatty() and not args.quiet and not args.verbose:
                terminal = Terminal()
                with terminal.progress() as progress:
                    answer = run_agent(
                        client,
                        args.prompt,
                        max_tool_rounds=args.max_tool_rounds,
                        model=args.model,
                        tools=tools,
                        on_event=progress,
                        temperature=0,
                    )
                if not answer or not answer.strip():
                    raise RuntimeError("The model returned an empty answer. Try again.")
                terminal.answer(answer)
                terminal.footer(args.model, progress)
            else:
                answer = run_agent(
                    client,
                    args.prompt,
                    args.verbose,
                    args.max_tool_rounds,
                    args.model,
                    tools=tools,
                    temperature=0,
                )
                if not answer or not answer.strip():
                    raise RuntimeError("The model returned an empty answer. Try again.")
                print(answer)
    except KeyboardInterrupt:
        print("Cancelled. Completed file changes remain.", file=sys.stderr)
        return 130
    except (APIError, RuntimeError) as error:
        Terminal(Console(stderr=True, markup=False, highlight=False)).error(
            describe_failure(error, args.base_url, args.model)
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
