from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

from app.cli import main
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call


class MlabCliTests(WorkspaceTestCase):
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
