import json

from app.session import Session
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call


class ProgressTests(WorkspaceTestCase):
    def test_events_follow_execution_order_and_bound_tool_content(self):
        content = "secret " * 500
        client = FakeClient(
            [
                assistant_message(
                    None,
                    [
                        tool_call(
                            "write",
                            "create_file",
                            json.dumps({"path": "new.txt", "content": content}),
                        )
                    ],
                ),
                assistant_message("Done"),
            ]
        )
        events = []
        Session(client, self.registry).turn("create", on_event=events.append)
        self.assertEqual([e.kind for e in events], ["request", "tool_start", "tool_end", "request"])
        self.assertNotIn("secret", events[1].summary)
        self.assertFalse(events[2].failed)
        self.assertTrue(all(len(e.summary) <= 500 for e in events))

    def test_tool_errors_are_reported_and_model_can_recover(self):
        client = FakeClient(
            [
                assistant_message(None, [tool_call("bad", "read_file", "{")]),
                assistant_message("Recovered"),
            ]
        )
        events = []
        self.assertEqual(
            Session(client, self.registry).turn("read", on_event=events.append), "Recovered"
        )
        self.assertTrue(events[2].failed)
        self.assertIn("invalid JSON", events[2].summary)
