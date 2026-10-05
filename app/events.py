"""Bounded progress notifications shared by agent and presentation."""

from dataclasses import dataclass
from typing import Callable, Literal


@dataclass(frozen=True)
class ProgressEvent:
    kind: Literal["request", "tool_start", "tool_end"]
    summary: str = ""
    failed: bool = False


ProgressCallback = Callable[[ProgressEvent], None]
