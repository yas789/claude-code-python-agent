import unittest
from io import StringIO
from pathlib import Path

from rich.console import Console

from app.events import ProgressEvent
from app.terminal import Terminal


class TerminalTests(unittest.TestCase):
    def test_progress_reports_tools_errors_and_elapsed_time(self):
        output = StringIO()
        terminal = Terminal(Console(file=output, force_terminal=False))
        with terminal.progress() as progress:
            progress(ProgressEvent("request"))
            progress(ProgressEvent("tool_start", "Using read_file path=notes.txt"))
            progress(ProgressEvent("tool_end", "ok (lines 1-3)"))
            progress(ProgressEvent("tool_start", "Using read_file path=missing"))
            progress(ProgressEvent("tool_end", "error: missing file", failed=True))
        terminal.footer("granite3.3:2b", progress)
        self.assertEqual((progress.tools, progress.failures), (2, 1))
        self.assertGreaterEqual(progress.elapsed, 0)
        self.assertIn("read_file path=notes.txt", output.getvalue())
        self.assertIn("error: missing file", output.getvalue())
        self.assertIn("2 tools · 1 errors", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())

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
