# mlab — Local Coding Agent

A terminal coding companion with editable prompts, follow-up conversations,
Markdown answers, and compact tool progress. It connects to local Ollama by
default and lets the model inspect and modify the current project through tools.

## Setup

Requires Python 3.14+, [uv](https://docs.astral.sh/uv/), and a running
[Ollama](https://ollama.com/) instance. Install from this checkout:

```sh
uv tool install --editable .
ollama pull granite3.3:2b
```

If Ollama is not already running, start it in another terminal:

```sh
ollama serve
```

If `mlab` is not on your PATH, run `uv tool update-shell` and reopen your terminal.
The editable installation follows changes in this checkout; reinstall after
changing dependencies. You can also run `uv run mlab` from the checkout.

## Open a conversation

Run `mlab` inside any project directory:

```sh
mlab
```

```text
  mlab
  Your local coding companion

  ~/git/my-project
  granite3.3:2b · Ollama

  Ask about your code or describe a change.
  /help for commands · Alt+Enter for a newline

› Explain this project

  ✓ list_files path=.
    ok (8 entries, truncated=False)

mlab
This project contains ...

──────────────────────────────────────────────
granite3.3:2b · 1 tools · 0 errors · 3.4s

›
```

Responses render Markdown and highlighted code. The transcript stays in native
terminal scrollback; a spinner shows activity while the model is working.
Follow-up prompts retain earlier answers and tool results. Sessions and input
history remain in memory until you exit. Responses appear when each model
request finishes; token streaming and saved sessions are future work.

### Commands and controls

| Command | Action |
| --- | --- |
| `/help` | Show commands and keyboard shortcuts |
| `/new` | Clear conversation context |
| `/model` | Show the current model |
| `/model <name>` | Switch model and clear context (same name keeps context) |
| `/exit` | Exit mlab |

- **Enter:** send the prompt.
- **Alt+Enter:** insert a newline (on macOS, Escape then Enter also works).
- **Up/Down:** navigate input/history.
- **Tab:** complete slash commands.
- **Ctrl+C:** clear input or cancel the active turn; completed file edits remain.
- **Ctrl+D:** exit from an empty input buffer.

Connection failures, missing models, timeouts, and empty answers display errors
and let you try another prompt. Model requests use temperature 0 and a 120-second
timeout, with automatic provider retries disabled. Models need native tool-call
support: `granite3.3:2b` passed the local file-read/follow-up smoke check;
`qwen2.5-coder:3b` emitted tool JSON as ordinary text in that check.

## One-shot usage

Run one prompt:

```sh
mlab --prompt "summarize this repository"
```

The short `-p` flag still works:

```sh
mlab -p "find where tools are defined"
```

Show tool activity:

```sh
mlab --verbose --prompt "read the README and list available tools"
```

Select a model explicitly:

```sh
mlab --model granite3.3:2b --prompt "inspect app/main.py"
```

Limit tool-call rounds:

```sh
mlab --max-tool-rounds 3 --prompt "summarize the codebase"
```

Choose a workspace:

```sh
mlab --workspace /path/to/project --prompt "search for TODOs"
```

Redirected one-shot stdout contains only the answer. `--verbose` adds bounded
tool logs to stderr. `--quiet` prints raw answers and suppresses progress and
metadata, including in interactive mode. Interactive startup requires a TTY;
use `--prompt` for scripts. Set `NO_COLOR=1` to disable colors.

The original `./your_program.sh --prompt "..."` launcher remains available and
defaults to local Granite. Its Python entry point (`app.main`) retains the
original OpenRouter configuration behavior.

## Provider configuration

`mlab` needs no API key for local Ollama. Runtime overrides:

| Setting | Default | Override |
| --- | --- | --- |
| Model | `granite3.3:2b` | `--model`, then `MLAB_MODEL` |
| API URL | `http://localhost:11434/v1` | `--base-url`, then `MLAB_BASE_URL`, then `OPENROUTER_BASE_URL` |
| API key | `ollama` placeholder | `MLAB_API_KEY`, then `OPENROUTER_API_KEY` |
| Workspace | Current directory | `--workspace` |

Example for OpenRouter:

```sh
export MLAB_API_KEY="your-key"
mlab --base-url https://openrouter.ai/api/v1 --model anthropic/claude-haiku-4.5
```

See [TERMINAL_DESIGN.md](TERMINAL_DESIGN.md) for design and future extension points.

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

Edits decode the original UTF-8 bytes without newline normalization and encode
the complete replacement before opening a staging file. Invalid UTF-8 replacement
text returns `error: edited content must be valid UTF-8 text` without mutation.
Untouched bytes retain their original CRLF, CR, or LF endings; multiline
`old_text` must match those actual endings exactly. `read_file` normalizes endings
to LF, so a single-line target is useful when reading a CRLF file through that tool.

The encoded edit is staged in a temporary file in the destination directory,
closed, assigned the original permission bits, and committed with `os.replace`.
Encoding, staging-write, permission-setting, and replacement failures before
commit leave the original intact. Staging files are cleaned up on normal errors
and Ctrl+C. Cancellation after replacement retains the completed edit; inspect
the file before retrying. In-workspace symlinks are resolved first, so editing
updates the target and preserves the symlink.

Atomic replacement swaps the destination directory entry for a new file;
permission bits are preserved, while inode identity and other inode metadata
are not guaranteed. This provides atomic visibility, not concurrent-writer
locking or crash-durable persistence.

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

Install the locked runtime and development dependencies:

```sh
uv sync --locked
```

Run all checks in the project environment; tests use scoped client mocks and
never replace the installed OpenAI package globally.

Run syntax checks:

```sh
uv run --locked python -m py_compile app/main.py
```

Run tests:

```sh
uv run --locked python -m unittest discover -s tests -p 'test_*.py'
```

Check formatting and lint:

```sh
uv run --locked ruff check app tests
uv run --locked ruff format --check app tests
```

Opt-in live Ollama verification (requires the installed command):

```sh
uv run --locked python tests/live_mlab.py --command "$HOME/.local/bin/mlab"
```

This creates a temporary workspace, verifies an actual file tool through the
installed command, and checks a real follow-up conversation. Ordinary tests use
scripted clients and include a pseudo-terminal startup/help/exit check.

## Architecture and Long-Term Plan

See [ROADMAP.md](ROADMAP.md) for the current architecture, proposed module
structure, and milestones toward a reliable edit-and-test coding assistant.

## Branch Flow

- `main` is the stable branch.
- `dev` is the development integration branch.
- `feature/*` branches are used for focused changes.

GitHub Actions runs tests for pushes to `main`, `dev`, and `feature/**`, and for pull requests into `main` or `dev`.
