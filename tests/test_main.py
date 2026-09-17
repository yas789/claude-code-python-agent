import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.modules["openai"] = SimpleNamespace(OpenAI=object)

from app import main


class MainTests(unittest.TestCase):
    def test_get_message_returns_first_choice_message(self):
        message = SimpleNamespace(content="hello")
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])

        self.assertIs(main.get_message(response), message)

    def test_get_message_raises_when_no_choices(self):
        response = SimpleNamespace(choices=[])

        with self.assertRaisesRegex(RuntimeError, "no choices in response"):
            main.get_message(response)

    def test_execute_tool_call_dispatches_registered_tool(self):
        tool_call = SimpleNamespace(
            function=SimpleNamespace(
                name="example_tool",
                arguments='{"value": "hello"}',
            )
        )

        with patch.dict(main.TOOL_FUNCTIONS, {"example_tool": lambda value: value.upper()}):
            self.assertEqual(main.execute_tool_call(tool_call), "HELLO")

    def test_execute_tool_call_raises_for_unknown_tool(self):
        tool_call = SimpleNamespace(
            function=SimpleNamespace(name="missing_tool", arguments="{}")
        )

        with self.assertRaisesRegex(RuntimeError, "unknown tool: missing_tool"):
            main.execute_tool_call(tool_call)

    def test_append_tool_results_adds_tool_messages(self):
        first_tool_call = SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(name="first_tool", arguments='{"value": "a"}'),
        )
        second_tool_call = SimpleNamespace(
            id="call_2",
            function=SimpleNamespace(name="second_tool", arguments='{"value": "b"}'),
        )
        message = SimpleNamespace(tool_calls=[first_tool_call, second_tool_call])
        messages = [{"role": "user", "content": "use tools"}]

        with patch.dict(
            main.TOOL_FUNCTIONS,
            {
                "first_tool": lambda value: value.upper(),
                "second_tool": lambda value: value * 2,
            },
        ):
            main.append_tool_results(messages, message)

        self.assertEqual(messages[1], message)
        self.assertEqual(
            messages[2],
            {"role": "tool", "tool_call_id": "call_1", "content": "A"},
        )
        self.assertEqual(
            messages[3],
            {"role": "tool", "tool_call_id": "call_2", "content": "bb"},
        )


if __name__ == "__main__":
    unittest.main()
