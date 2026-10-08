"""Opt-in installed-command and real-model smoke check (excluded from discovery)."""

import argparse
import os
import shutil
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

from rich.console import Console

from app.chat import chat
from app.main import LocalTools, create_tool_registry
from app.session import Session
from app.settings import LOCAL_BASE_URL, LOCAL_MODEL, Settings
from app.terminal import Terminal
from app.workspace import Workspace


class ScriptedInput:
    def __init__(self, prompts):
        self.prompts = iter(prompts)

    def read(self):
        return next(self.prompts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=LOCAL_MODEL)
    parser.add_argument(
        "--command", default=shutil.which("mlab"), help="Installed mlab executable."
    )
    args = parser.parse_args()
    command = args.command
    if not command:
        raise SystemExit("Install first: uv tool install --editable .")

    with tempfile.TemporaryDirectory(prefix="mlab-live-") as directory:
        root = Path(directory).resolve()
        marker = "blue"
        (root / "notes.txt").write_text(f"The project marker is {marker}.\n")
        prompt = "Read notes.txt using your tools and report the project marker. Do not edit files."
        result = subprocess.run(
            [command, "--model", args.model, "--verbose", "--prompt", prompt],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "MLAB_BASE_URL": LOCAL_BASE_URL, "MLAB_API_KEY": "ollama"},
            check=True,
        )
        if marker not in result.stdout.lower() or "Using read_file" not in result.stderr:
            raise AssertionError(f"Installed CLI did not read the marker: {result}")
        print("Installed mlab read a file from a different working directory.")

        output = StringIO()
        terminal = Terminal(Console(file=output, force_terminal=False))
        with Settings(LOCAL_BASE_URL, "ollama", args.model).create_client() as client:
            session = Session(client, create_tool_registry(LocalTools(Workspace(root))), args.model)
            chat(
                session,
                terminal,
                ScriptedInput(
                    [
                        prompt,
                        "What was the exact project marker from your previous answer? Answer from memory.",
                        "/exit",
                    ]
                ),
            )
        transcript = output.getvalue()
        if "read_file" not in transcript or transcript.lower().count(marker) < 2:
            raise AssertionError(f"Live conversation failed:\n{transcript}")
        print(transcript)
        print("Live tool execution and remembered follow-up passed.")


if __name__ == "__main__":
    main()
