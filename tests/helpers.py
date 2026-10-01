import tempfile
import unittest
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
        self.messages = messages
        self.calls = []

    def create(self, model, messages, tools):
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        return SimpleNamespace(choices=[SimpleNamespace(message=self.messages.pop(0))])


class FakeClient:
    def __init__(self, messages):
        self.completions = FakeCompletions(messages)
        self.chat = SimpleNamespace(completions=self.completions)


def fixture_text(name):
    return (FIXTURES / name).read_text().strip()


def assistant_message(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def final_message_without_tool_calls(content):
    return SimpleNamespace(content=content)


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )
