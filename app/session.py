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
        start = len(self.messages)
        try:
            answer = run_agent(
                self.client,
                prompt,
                max_tool_rounds=self.max_tool_rounds,
                model=self.model,
                tools=self.tools,
                messages=self.messages,
                temperature=0,
                **kwargs,
            )
            if not answer or not answer.strip():
                raise RuntimeError("The model returned an empty answer. Try again or use /new.")
            return answer
        except Exception, KeyboardInterrupt:
            self._close_failed_turn(start)
            raise

    def _close_failed_turn(self, start):
        """Preserve completed work and close any unanswered tool calls."""
        turn = self.messages[start:]
        answered = {
            message["tool_call_id"]
            for message in turn
            if isinstance(message, dict) and message.get("role") == "tool"
        }
        for message in turn:
            for call in getattr(message, "tool_calls", None) or []:
                if call.id not in answered:
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": "error: turn interrupted; tool completion is unknown",
                        }
                    )
        self.messages.append(
            {
                "role": "assistant",
                "content": "This turn stopped before completion. Completed file changes remain; "
                "inspect the workspace before retrying changes.",
            }
        )
