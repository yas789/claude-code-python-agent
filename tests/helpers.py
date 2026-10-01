import tempfile
import unittest
from collections import deque
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import main

FIXTURES = Path(__file__).parent / "fixtures"


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name).resolve()
        workspace_patch = patch.object(main, "WORKSPACE_ROOT", self.root)
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)
        # Temporary adapter until tools accept an explicit workspace.
        self.tools = main

    def run_agent(self, *args, **kwargs):
        return main.run_agent(*args, **kwargs)


class FakeCompletions:
    def __init__(self, messages):
        self._responses = deque(messages)
        self.calls = []

    def create(self, model, messages, tools):
        if not self._responses:
            raise AssertionError(
                f"FakeCompletions scripted responses exhausted on call {len(self.calls) + 1} "
                f"(model={model!r}); add a scripted response for this call"
            )
        self.calls.append(
            {"model": model, "messages": deepcopy(messages), "tools": deepcopy(tools)}
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=self._responses.popleft())])


class FakeClient:
    def __init__(self, messages):
        self.completions = FakeCompletions(messages)
        self.chat = SimpleNamespace(completions=self.completions)


def fixture_text(name):
    return (FIXTURES / name).read_text().strip()


def tool_result(messages, call_id):
    results = [
        message
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "tool"
        and message.get("tool_call_id") == call_id
    ]
    if len(results) != 1:
        raise AssertionError(
            f"Expected exactly one tool result for tool_call_id={call_id!r}; found {len(results)}"
        )
    return results[0]


def assistant_message(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def final_message_without_tool_calls(content):
    return SimpleNamespace(content=content)


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )
