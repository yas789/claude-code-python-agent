# Claude Code Python Agent

A small command-line coding agent that talks to an OpenAI-compatible API and lets the model inspect and modify the local workspace through tools.

## Setup

Set your OpenRouter API key:

```sh
export OPENROUTER_API_KEY="your-key"
```

Optional:

```sh
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
```

## Usage

Run one prompt:

```sh
./your_program.sh --prompt "summarize this repository"
```

The short `-p` flag still works:

```sh
./your_program.sh -p "find where tools are defined"
```

Show tool activity:

```sh
./your_program.sh --verbose --prompt "read the README and list available tools"
```

Use a different model:

```sh
./your_program.sh --model anthropic/claude-haiku-4.5 --prompt "inspect app/main.py"
```

Limit tool-call rounds:

```sh
./your_program.sh --max-tool-rounds 3 --prompt "summarize the codebase"
```

Choose a workspace:

```sh
./your_program.sh --workspace /path/to/project --prompt "search for TODOs"
```

## Tools

The model can request these tools:

- `read_file(path, offset=1, limit=200, max_chars=16000)` reads a bounded file
  section inside the workspace and returns JSON text with continuation metadata.
- `list_files(path, offset=1, limit=100, max_chars=16000)` returns a bounded page
  of sorted directory-entry names.
- `edit_file(path, old_text, new_text)` replaces one nonempty exact text match
  and returns a compact JSON receipt.
- `create_file(path, content)` creates a new UTF-8 file without overwriting and
  returns a compact JSON receipt.
- `search_files(query, path, limit=20, max_chars=16000, offset=1)` returns a
  bounded page of case-sensitive matching lines.

Tool paths are restricted to the configured workspace.

**Successful results from all five tools are JSON text.** Errors are still
returned to the model as `error: ...`. Listing, search, editing, and creation
previously returned plain text; callers should now decode their JSON results.

### Bounded File Reads

Ask the agent to inspect a section:

```sh
./your_program.sh --prompt "Read lines 50–75 of app/main.py"
```

The model can call `read_file` with these arguments:

```json
{"path": "app/main.py", "offset": 50, "limit": 26, "max_chars": 16000}
```

`offset` is a 1-based starting line. `limit` defaults to 200 and must be between
1 and 2,000. `max_chars` defaults to 16,000 and must be between 1 and 65,536.
All three numeric arguments must be integers; booleans are rejected.
Only `path` is required.

**Return format:** `read_file` now returns JSON text instead of raw file text.
For a three-line file containing `alpha`, `beta`, and `gamma`, a read with
`offset=2` and `limit=1` returns:

```json
{
  "content": "beta\n",
  "start_line": 2,
  "end_line": 2,
  "truncated": true,
  "next_offset": 3
}
```

The agent can continue with the same path and `offset=3`. `truncated` means
there is more content after the returned range; `next_offset` identifies the
first unread line. At EOF, `truncated` is false and `next_offset` is null. Empty
files and offsets beyond EOF return empty content and a null `end_line`.

Reads use UTF-8, normalize CRLF/CR newlines to LF, and preserve complete lines,
including a final line without a newline. The character budget counts decoded
content characters, including normalized newlines; JSON escaping and metadata
add serialization overhead. A character limit may return fewer lines than
requested. If the first selected line exceeds the budget, the tool returns an
actionable error: increase `max_chars` within its ceiling or choose another
offset. Lines larger than the hard ceiling cannot be returned by this tool.

Both selected and skipped lines are read incrementally with bounded buffers;
reading a later section still requires scanning the preceding text.

### Paginated Directory Listings

`list_files` sorts immediate entry names and returns:

```json
{
  "entries": ["README.md", "app"],
  "truncated": true,
  "next_offset": 3
}
```

Ordering is case-sensitive lexical order. `offset` is a 1-based entry index,
`limit` defaults to 100 with a
maximum of 2,000, and `max_chars` defaults to 16,000 with a maximum of 65,536.
The character budget counts entry-name characters, excluding JSON overhead.
Names are never split. If the first selected name cannot fit, increase the
budget. Empty directories and offsets beyond the last entry return empty
`entries`, false `truncated`, and null `next_offset`.

Continue with the returned `next_offset` and the same path. Pagination assumes
the directory has not changed between calls. Output is bounded; sorting still
collects the directory's entry names in memory.

### Bounded Search and Continuation

Example model arguments:

```json
{"query": "TODO", "path": ".", "limit": 20, "max_chars": 16000, "offset": 1}
```

Example result:

```json
{
  "results": [
    {"path": "app/main.py", "line": 12, "text": "# TODO: add tests", "text_truncated": false}
  ],
  "truncated": true,
  "next_offset": 2
}
```

- Queries are nonempty, case-sensitive substrings of at most 4,096 characters
  and cannot contain CR or LF. One result represents one matching physical line,
  even if the query occurs several times on that line.
- `limit` defaults to 20 and has a ceiling of 200. `max_chars` defaults to 16,000
  and has a ceiling of 65,536; it counts total snippet characters, excluding
  paths, metadata, and JSON overhead.
- `offset` is a **1-based matching-line index**, not a file line number. Files
  in each directory are searched in sorted order before its sorted child
  directories. Continue with `next_offset`, the same query/path, and an unchanged
  tree. Each continuation rescans earlier matches rather than retaining a cursor.
- `truncated` means additional matching lines remain. `text_truncated` means an
  included snippet was clipped; it is independent of page truncation. A clipped
  snippet is a line prefix and may not contain the query. Use `read_file` with
  the returned path and line number to inspect it further.
- No matches, or an offset beyond the final match, return empty `results`, false
  `truncated`, and null `next_offset`.

Search uses UTF-8 with normalized LF line numbers and bounded chunk buffers,
including for long lines. It detects substring matches across chunks without
matching across physical lines. Ignored directories (`.git`, `.venv`, and
`__pycache__`) are pruned before traversal; directory symlinks are not followed.
Outside-workspace, broken, non-file, and unreadable paths are skipped. Decoding
errors stop searching that file; matches already yielded from it may remain.
Exact truncation detection may require scanning the remaining tree to find
another match or establish EOF; output budgets do not impose a runtime budget.

Listing and search numeric arguments require positive integers; booleans are
rejected. Only their original arguments (`path`, or `query` and `path`) remain
required.

### Write Validation and Receipts

`edit_file` requires a nonempty string `old_text` that occurs exactly once.
`new_text` must be a string and can be empty to delete the match. A successful
edit returns:

```json
{"status": "updated", "path": "example.txt", "replacements": 1}
```

`create_file` requires string content encodable as UTF-8, allows empty content,
and requires an existing parent directory. It uses exclusive creation so an
existing or concurrently created file is not overwritten. A successful creation
returns:

```json
{"status": "created", "path": "example.txt", "chars_written": 11}
```

Receipt paths are resolved workspace-relative paths. `chars_written` counts
input characters, not UTF-8 bytes. Receipts do not echo file content, and output
budgets never truncate requested write content. Invalid argument types and empty
edit targets are rejected before mutation.

## Development

Run syntax checks:

```sh
python3 -m py_compile app/main.py
```

Run tests:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Architecture and Long-Term Plan

See [ROADMAP.md](ROADMAP.md) for the current architecture, proposed module
structure, and milestones toward a reliable edit-and-test coding assistant.

## Branch Flow

- `main` is the stable branch.
- `dev` is the development integration branch.
- `feature/*` branches are used for focused changes.

GitHub Actions runs tests for pushes to `main`, `dev`, and `feature/**`, and for pull requests into `main` or `dev`.
