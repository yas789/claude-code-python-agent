"""In-memory conversations, independent of the terminal interface."""

from dataclasses import dataclass, field

from app.config import DEFAULT_MAX_TOOL_ROUNDS
from app.main import run_agent
from app.registry import ToolRegistry
from app.settings import LOCAL_MODEL


@dataclass
class Session:
    client: object
    tools: ToolRegistry
    model: str = LOCAL_MODEL
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS
    messages: list = field(default_factory=list)

    def reset(self):
        self.messages.clear()

    def turn(self, prompt, **kwargs):
        return run_agent(
            self.client,
            prompt,
            max_tool_rounds=self.max_tool_rounds,
            model=self.model,
            tools=self.tools,
            messages=self.messages,
            **kwargs,
        )
