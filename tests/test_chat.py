from io import StringIO
from unittest.mock import Mock, patch

from rich.console import Console

from app.chat import chat
from app.session import Session
from app.terminal import Terminal
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message


class ChatTests(WorkspaceTestCase):
    def test_turn_failure_and_cancellation_allow_another_prompt(self):
        _, session, output, terminal, editor = self.setup_chat(
            [], ["first", "second", "third", "/exit"]
        )
        with patch.object(
            session,
            "turn",
            side_effect=[RuntimeError("budget exhausted"), KeyboardInterrupt(), "Recovered"],
        ):
            self.assertEqual(chat(session, terminal, editor), 0)
        for expected in ("budget exhausted", "Cancelled", "Recovered"):
            self.assertIn(expected, output.getvalue())

    def test_model_switch_changes_requests_and_clears_context(self):
        client, session, output, terminal, editor = self.setup_chat(
            [assistant_message("one"), assistant_message("two")],
            ["first", "/model", "/model qwen2.5-coder:3b", "second", "/exit"],
        )
        chat(session, terminal, editor)
        self.assertIn("Current model: granite3.3:2b", output.getvalue())
        self.assertEqual(client.completions.calls[1]["model"], "qwen2.5-coder:3b")
        self.assertEqual(
            client.completions.calls[1]["messages"], [{"role": "user", "content": "second"}]
        )

    def test_same_or_invalid_model_retains_context(self):
        _, session, output, terminal, editor = self.setup_chat(
            [assistant_message("one")],
            ["first", "/model granite3.3:2b", "/model too many names", "/exit"],
        )
        chat(session, terminal, editor)
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.model, "granite3.3:2b")
        self.assertIn("single model name", output.getvalue())

    def test_commands_stay_local_and_new_clears_context(self):
        client, session, output, terminal, editor = self.setup_chat(
            [assistant_message("one"), assistant_message("two")],
            ["first", "/help", "/unknown", "/new", "second", "/exit"],
        )
        self.assertEqual(chat(session, terminal, editor), 0)
        self.assertEqual(len(client.completions.calls), 2)
        self.assertEqual(
            client.completions.calls[1]["messages"], [{"role": "user", "content": "second"}]
        )
        self.assertIn("Alt+Enter", output.getvalue())
        self.assertIn("Unknown command", output.getvalue())

    def test_invalid_command_arguments_do_not_reset_session(self):
        client, session, output, terminal, editor = self.setup_chat(
            [assistant_message("one")], ["first", "/new unexpected", "/exit"]
        )
        chat(session, terminal, editor)
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(len(client.completions.calls), 1)
        self.assertIn("does not accept arguments", output.getvalue())

    def setup_chat(self, responses, inputs):
        client = FakeClient(responses)
        session = Session(client, self.registry)
        output = StringIO()
        terminal = Terminal(Console(file=output, force_terminal=False))
        editor = Mock()
        editor.read.side_effect = inputs
        return client, session, output, terminal, editor

    def test_interactive_follow_up_and_eof(self):
        client, session, output, terminal, editor = self.setup_chat(
            [assistant_message("First answer"), assistant_message("Follow-up answer")],
            ["first", "follow up", EOFError()],
        )
        self.assertEqual(chat(session, terminal, editor), 0)
        self.assertEqual(client.completions.calls[1]["messages"][-2]["content"], "First answer")
        for expected in ("First answer", "Follow-up answer", "Goodbye."):
            self.assertIn(expected, output.getvalue())

    def test_empty_input_and_input_interrupt_do_not_call_model(self):
        client, session, _, terminal, editor = self.setup_chat(
            [], [" ", KeyboardInterrupt(), EOFError()]
        )
        self.assertEqual(chat(session, terminal, editor), 0)
        self.assertEqual(client.completions.calls, [])
