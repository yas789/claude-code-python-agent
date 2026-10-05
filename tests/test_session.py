from unittest.mock import patch

from app.session import Session
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call, tool_result


class SessionTests(WorkspaceTestCase):
    def test_failed_request_retains_valid_history_for_retry(self):
        client = FakeClient([assistant_message("Recovered")])
        session = Session(client, self.registry)
        with patch("app.main.create_chat_completion", side_effect=RuntimeError("offline")):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                session.turn("first")
        self.assertEqual(session.turn("retry"), "Recovered")
        messages = client.completions.calls[-1]["messages"]
        self.assertEqual(messages[-2]["role"], "assistant")
        self.assertIn("stopped", messages[-2]["content"])

    def test_interrupted_tools_keep_receipts_and_close_pending_calls(self):
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [
                        tool_call("write", "create_file", '{"path":"new.txt","content":"saved"}'),
                        tool_call("pending", "read_file", '{"path":"new.txt"}'),
                    ],
                ),
                assistant_message("Recovered"),
            ]
        )
        session = Session(client, self.registry)
        execute = self.registry.execute

        def interrupt_second(call):
            if call.name == "read_file":
                raise KeyboardInterrupt
            return execute(call)

        with patch.object(self.registry, "execute", side_effect=interrupt_second):
            with self.assertRaises(KeyboardInterrupt):
                session.turn("create then read")
        self.assertEqual((self.root / "new.txt").read_text(), "saved")
        self.assertIn('"created"', tool_result(session.messages, "write")["content"])
        self.assertIn("unknown", tool_result(session.messages, "pending")["content"])
        self.assertEqual(session.turn("inspect again"), "Recovered")

    def test_budget_failure_keeps_completed_tool_results(self):
        client = FakeClient(
            [
                assistant_message(None, [tool_call("list", "list_files", '{"path":"."}')]),
                assistant_message("Recovered"),
            ]
        )
        session = Session(client, self.registry, max_tool_rounds=1)
        with self.assertRaisesRegex(RuntimeError, "maximum tool call rounds"):
            session.turn("inspect")
        self.assertIn("entries", tool_result(session.messages, "list")["content"])
        self.assertEqual(session.turn("summarize"), "Recovered")

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
