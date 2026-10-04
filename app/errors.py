class ToolError(RuntimeError):
    """An expected tool validation or filesystem failure."""


class AgentError(RuntimeError):
    """An agent protocol or budget failure."""


class ConfigurationError(RuntimeError):
    """A startup configuration failure."""
