"""Scrollable terminal presentation for mlab."""

import re
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text


def clean_text(value):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(value))


class Terminal:
    def __init__(self, console=None):
        self.console = console or Console(highlight=False, markup=False, emoji=False)

    def welcome(self, workspace, model, base_url):
        root = Path(workspace)
        try:
            path = "~/" + str(root.relative_to(Path.home()))
        except ValueError:
            path = str(root)
        provider = "Ollama" if urlparse(base_url).port == 11434 else "OpenAI-compatible API"
        self.console.print()
        self.console.print(Text("  mlab", style="bold cyan"))
        self.console.print("  Your local coding companion", style="dim")
        self.console.print()
        self.console.print(Text("  " + clean_text(path), style="dim"))
        self.console.print(Text(f"  {clean_text(model)} · {provider}", style="dim"))
        self.console.print()
        self.console.print("  Ask about your code or describe a change.")
        self.console.print("  /help for commands · Alt+Enter for a newline", style="dim")
        self.console.print()

    def answer(self, content):
        self.console.print(Text("mlab", style="bold cyan"))
        self.console.print(Markdown(clean_text(content or "(No text response.)")))
        self.console.print()

    def notice(self, message):
        self.console.print(Text(clean_text(message), style="dim"))

    def error(self, message):
        self.console.print(Text(clean_text(message), style="red"))

    def progress(self):
        return TurnProgress(self.console)

    def help(self, commands):
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column()
        for name, description in commands.items():
            table.add_row(Text(name), Text(description))
        self.console.print(table)
        self.notice("Enter sends · Alt+Enter adds a newline · Up/Down navigate history")
        self.notice("Tab completes commands · Ctrl+C cancels/clears · Ctrl+D exits")

    def footer(self, model, progress):
        self.console.rule(style="dim")
        self.notice(
            f"{model} · {progress.tools} tools · {progress.failures} errors · "
            f"{progress.elapsed:.1f}s"
        )
        self.console.print()


class TurnProgress:
    def __init__(self, console):
        self.console = console
        self.tools = 0
        self.failures = 0
        self.elapsed = 0.0
        self.pending = ""
        self.status = None

    def __enter__(self):
        self.started = monotonic()
        if self.console.is_terminal:
            self.status = self.console.status(Text("Working…", style="cyan"), spinner="dots")
            self.status.start()
        return self

    def __exit__(self, *_):
        if self.status:
            self.status.stop()
        self.elapsed = monotonic() - self.started

    def __call__(self, event):
        if event.kind == "request" and self.status:
            self.status.update(Text("Thinking…", style="cyan"))
        elif event.kind == "tool_start":
            self.pending = clean_text(event.summary.removeprefix("Using "))
            if self.status:
                self.status.update(Text(self.pending, style="cyan"))
        elif event.kind == "tool_end":
            self.tools += 1
            self.failures += int(event.failed)
            symbol = "✗" if event.failed else "✓"
            self.console.print(
                Text(f"  {symbol} {self.pending}", style="red" if event.failed else "green")
            )
            self.console.print(Text("    " + clean_text(event.summary), style="dim"))
