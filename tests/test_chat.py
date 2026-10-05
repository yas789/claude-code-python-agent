from io import StringIO
from unittest.mock import Mock

from rich.console import Console

from app.chat import chat
from app.session import Session
from app.terminal import Terminal
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message


class ChatTests(WorkspaceTestCase):
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
