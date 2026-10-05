from app.session import Session
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call, tool_result


class SessionTests(WorkspaceTestCase):
    def test_follow_up_retains_answer_and_file_tool_exchange(self):
        (self.root / "notes.txt").write_text("remember cobalt")
        client = FakeClient(
            [
                assistant_message(None, [tool_call("read", "read_file", '{"path":"notes.txt"}')]),
                assistant_message("The word is cobalt."),
                assistant_message("cobalt"),
            ]
        )
        session = Session(client, self.registry)
        session.turn("Read notes.txt")
        self.assertEqual(session.turn("What was the word?"), "cobalt")
        messages = client.completions.calls[-1]["messages"]
        self.assertIn("remember cobalt", tool_result(messages, "read")["content"])
        self.assertEqual(messages[-2], {"role": "assistant", "content": "The word is cobalt."})
        self.assertEqual(messages[-1], {"role": "user", "content": "What was the word?"})

    def test_reset_removes_previous_context(self):
        client = FakeClient([assistant_message("one"), assistant_message("two")])
        session = Session(client, self.registry)
        session.turn("first")
        session.reset()
        session.turn("second")
        self.assertEqual(
            client.completions.calls[-1]["messages"], [{"role": "user", "content": "second"}]
        )
