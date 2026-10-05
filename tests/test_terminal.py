import unittest
from io import StringIO
from pathlib import Path

from rich.console import Console

from app.terminal import Terminal


class TerminalTests(unittest.TestCase):
    def test_narrow_plain_welcome_and_markdown_are_readable(self):
        output = StringIO()
        terminal = Terminal(Console(file=output, width=36, force_terminal=False))
        terminal.welcome(Path.cwd(), "granite3.3:2b", "http://localhost:11434/v1")
        terminal.answer("## Dependencies\n\n- openai\n\n```python\nprint('hello')\n```")
        text = output.getvalue()
        for expected in ("mlab", "granite3.3:2b", "Ollama", "Dependencies", "openai", "hello"):
            self.assertIn(expected, text)
        self.assertNotIn("\x1b", text)
        self.assertTrue(all(len(line) <= 36 for line in text.splitlines()))

    def test_metadata_is_literal_and_terminal_controls_are_removed(self):
        output = StringIO()
        terminal = Terminal(Console(file=output, force_terminal=False))
        terminal.notice("[bold]literal[/bold]\x1b[2J")
        terminal.error("bad\x07model")
        self.assertIn("[bold]literal[/bold]", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())
        self.assertNotIn("\x07", output.getvalue())
