"""Scrollable terminal presentation for mlab."""

import re
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.markdown import Markdown
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
