import os
import pty
import select
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from time import monotonic
from unittest.mock import MagicMock, patch

from app.cli import main
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call


class MlabCliTests(WorkspaceTestCase):
    def test_real_terminal_opens_help_and_exits_without_model_request(self):
        master, slave = pty.openpty()
        process = subprocess.Popen(
            [sys.executable, "-m", "app.cli"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=self.root,
            env={**os.environ, "PROMPT_TOOLKIT_NO_CPR": "1", "MLAB_MODEL": "granite3.3:2b"},
        )
        os.close(slave)
        transcript = b""
        help_sent = exit_sent = False
        deadline = monotonic() + 10
        try:
            while monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    transcript += chunk
                if not help_sent and "› ".encode() in transcript:
                    os.write(master, b"/help\r")
                    help_sent = True
                if help_sent and not exit_sent and b"Ctrl+D exits" in transcript:
                    os.write(master, b"/exit\r")
                    exit_sent = True
                if process.poll() is not None:
                    break
            text = transcript.decode(errors="replace")
            self.assertTrue(help_sent and exit_sent, text)
            self.assertEqual(process.wait(timeout=2), 0, text)
            self.assertIn("Your local coding companion", text)
            self.assertNotIn("Traceback", text)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            os.close(master)

    def test_redirected_verbose_output_separates_answer_from_tools(self):
        (self.root / "notes.txt").write_text("hello")
        client = FakeClient(
            [
                assistant_message(None, [tool_call("read", "read_file", '{"path":"notes.txt"}')]),
                assistant_message("# Answer\nhello"),
            ]
        )
        manager = MagicMock()
        manager.__enter__.return_value = client
        stdout, stderr = StringIO(), StringIO()
        with (
            patch("app.settings.Settings.create_client", return_value=manager),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = main(["--prompt", "read notes", "--workspace", str(self.root), "--verbose"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "# Answer\nhello\n")
        self.assertIn("Using read_file", stderr.getvalue())
        self.assertNotIn("\x1b", stdout.getvalue())

    def test_quiet_one_shot_has_only_answer(self):
        manager = MagicMock()
        manager.__enter__.return_value = FakeClient([assistant_message("plain answer")])
        stdout, stderr = StringIO(), StringIO()
        with (
            patch("app.settings.Settings.create_client", return_value=manager),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            self.assertEqual(main(["--prompt", "hello", "--quiet"]), 0)
        self.assertEqual(stdout.getvalue(), "plain answer\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_non_tty_startup_does_not_create_client_or_input_editor(self):
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("app.settings.Settings.create_client") as create,
            patch("app.cli.Input") as editor,
            redirect_stderr(StringIO()) as stderr,
        ):
            self.assertEqual(main([]), 2)
        create.assert_not_called()
        editor.assert_not_called()
        self.assertIn("--prompt", stderr.getvalue())
