"""Static defaults and limits for the coding agent and workspace tools."""

DEFAULT_MODEL: str = "anthropic/claude-haiku-4.5"
DEFAULT_MAX_TOOL_ROUNDS: int = 10
DEFAULT_SEARCH_RESULTS: int = 20
MAX_SEARCH_RESULTS: int = 200
MAX_SEARCH_QUERY_CHARS: int = 4096
DEFAULT_READ_LINES: int = 200
MAX_READ_LINES: int = 2000
DEFAULT_READ_CHARS: int = 16000
MAX_READ_CHARS: int = 65536
DEFAULT_LIST_ENTRIES: int = 100
MAX_LIST_ENTRIES: int = 2000
DEFAULT_TOOL_CHARS: int = 16000
MAX_TOOL_CHARS: int = 65536
SEARCH_CHUNK_CHARS: int = 4096
IGNORED_SEARCH_DIRS: frozenset[str] = frozenset({".git", ".venv", "__pycache__"})
