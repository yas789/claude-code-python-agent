from app.config import (
    DEFAULT_LIST_ENTRIES,
    DEFAULT_READ_CHARS,
    DEFAULT_READ_LINES,
    DEFAULT_SEARCH_RESULTS,
    DEFAULT_TOOL_CHARS,
    MAX_LIST_ENTRIES,
    MAX_READ_CHARS,
    MAX_READ_LINES,
    MAX_SEARCH_QUERY_CHARS,
    MAX_SEARCH_RESULTS,
    MAX_TOOL_CHARS,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a bounded line range from the local workspace. Returns JSON with content, start_line, end_line, truncated, and next_offset; use next_offset to continue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "The 1-based starting line (default: 1).",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_READ_LINES,
                        "default": DEFAULT_READ_LINES,
                        "description": "Maximum number of lines to read (default: 200; maximum: 2000).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_READ_CHARS,
                        "default": DEFAULT_READ_CHARS,
                        "description": "Content character budget including newlines (default: 16000; maximum: 65536). Complete lines only; increase this budget if a selected line is too long.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List sorted entry names in the local workspace. Returns JSON with entries, truncated, and next_offset; continue with next_offset on an unchanged directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to list.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "The 1-based starting entry.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_LIST_ENTRIES,
                        "default": DEFAULT_LIST_ENTRIES,
                        "description": "Maximum entries to return (default: 100; maximum: 2000).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_CHARS,
                        "default": DEFAULT_TOOL_CHARS,
                        "description": "Entry-name character budget, excluding JSON overhead (default: 16000; maximum: 65536).",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace one nonempty exact text match in a UTF-8 file in the local workspace. Returns a JSON receipt with status, resolved workspace-relative path, and replacements. An empty new_text deletes the match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to edit.",
                    },
                    "old_text": {
                        "type": "string",
                        "minLength": 1,
                        "description": "The nonempty exact existing text to replace; must occur once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new UTF-8 file in the local workspace without overwriting existing files. Empty content is allowed. Returns a JSON receipt with status, resolved workspace-relative path, and chars_written; content is written in full.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path of the file to create.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the new file.",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search UTF-8 files in the local workspace for a case-sensitive substring. Returns JSON results with path, line, text, and text_truncated, plus truncated and next_offset. Continue with next_offset and the same query/path on an unchanged tree. Clipped text is a line prefix and may omit the query; use read_file at that line for more detail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_SEARCH_QUERY_CHARS,
                        "pattern": "^[^\r\n]+$",
                        "description": "Nonempty, case-sensitive substring without CR/LF (maximum: 4096 characters).",
                    },
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to search.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1,
                        "description": "The 1-based matching-line offset, not a file line number. Continuation rescans the unchanged tree.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_SEARCH_RESULTS,
                        "default": DEFAULT_SEARCH_RESULTS,
                        "description": "Maximum matching lines (default: 20; maximum: 200).",
                    },
                    "max_chars": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_CHARS,
                        "default": DEFAULT_TOOL_CHARS,
                        "description": "Total snippet-character budget excluding metadata and JSON overhead (default: 16000; maximum: 65536).",
                    },
                },
                "required": ["query", "path"],
                "additionalProperties": False,
            },
        },
    },
]
