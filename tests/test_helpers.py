import unittest
from copy import deepcopy
from types import SimpleNamespace

from tests.helpers import FakeCompletions, assistant_message, tool_call, tool_result


class FakeCompletionsTests(unittest.TestCase):
    def test_script_is_copied_and_consumed_in_order_without_changing_input(self):
        first = assistant_message("first")
        second = assistant_message("second")
        scripted = [first, second]
        completions = FakeCompletions(scripted)
        scripted.append(assistant_message("not in the original script"))

        self.assertIs(completions.create("model", [], []).choices[0].message, first)
        self.assertIs(completions.create("model", [], []).choices[0].message, second)
        self.assertEqual(scripted[:2], [first, second])
        self.assertEqual(len(scripted), 3)
        with self.assertRaisesRegex(AssertionError, "scripted responses exhausted"):
            completions.create("model", [], [])

    def test_exhaustion_identifies_attempted_call_without_recording_it(self):
        for response_count in (0, 1):
            with self.subTest(response_count=response_count):
                completions = FakeCompletions([assistant_message("done")] * response_count)
                for _ in range(response_count):
                    completions.create("test/model", [], [])
                history = deepcopy(completions.calls)
                with self.assertRaisesRegex(
                    AssertionError,
                    rf"scripted responses exhausted on call {response_count + 1} .*test/model.*"
                    r"add a scripted response",
                ):
                    completions.create("test/model", [{"role": "user"}], [])
                self.assertEqual(completions.calls, history)

    def test_call_history_keeps_independent_nested_message_and_tool_snapshots(self):
        completions = FakeCompletions([assistant_message("one"), assistant_message("two")])
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "original"}]},
            assistant_message(None, [tool_call("read", "read_file", '{"path": "a.txt"}')]),
        ]
        tools = [{"function": {"parameters": {"required": ["path"]}}}]
        original_messages = deepcopy(messages)
        original_tools = deepcopy(tools)
        completions.create("first/model", messages, tools)

        messages[0]["content"][0]["text"] = "changed"
        messages[1].tool_calls[0].function.arguments = '{"path": "b.txt"}'
        messages.append({"role": "tool", "tool_call_id": "read", "content": "result"})
        tools[0]["function"]["parameters"]["required"].append("offset")
        completions.create("second/model", messages, tools)
        second_messages = deepcopy(messages)
        second_tools = deepcopy(tools)
        messages[0]["content"].clear()
        messages[1].tool_calls.clear()
        tools[0]["function"]["parameters"]["required"].clear()
        messages.clear()
        tools.clear()

        self.assertEqual(
            completions.calls,
            [
                {"model": "first/model", "messages": original_messages, "tools": original_tools},
                {"model": "second/model", "messages": second_messages, "tools": second_tools},
            ],
        )


class ToolResultTests(unittest.TestCase):
    def test_lookup_selects_only_tool_dict_with_matching_call_id(self):
        expected = {"role": "tool", "tool_call_id": "target", "content": "found"}
        messages = [
            {"role": "tool", "tool_call_id": "other", "content": "other result"},
            SimpleNamespace(role="tool", tool_call_id="target"),
            {"role": "assistant", "tool_call_id": "target"},
            {},
            expected,
            {"role": "tool"},
        ]
        self.assertIs(tool_result(messages, "target"), expected)
        self.assertIs(tool_result(list(reversed(messages)), "target"), expected)

    def test_absent_result_reports_call_id_and_zero_matches(self):
        messages = [{"role": "tool", "tool_call_id": "other"}]
        with self.assertRaisesRegex(AssertionError, "exactly one tool result.*'missing'; found 0"):
            tool_result(messages, "missing")

    def test_duplicate_results_report_call_id_and_match_count(self):
        messages = [
            {"role": "tool", "tool_call_id": "duplicate", "content": "first"},
            {"role": "tool", "tool_call_id": "duplicate", "content": "second"},
        ]
        with self.assertRaisesRegex(
            AssertionError, "exactly one tool result.*'duplicate'; found 2"
        ):
            tool_result(messages, "duplicate")
