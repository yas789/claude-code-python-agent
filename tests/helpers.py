import sys
from pathlib import Path
from types import SimpleNamespace

sys.modules["openai"] = SimpleNamespace(OpenAI=object)

FIXTURES = Path(__file__).parent / "fixtures"


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
