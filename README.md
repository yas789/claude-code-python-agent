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
- `list_files(path)` lists a directory inside the workspace.
- `edit_file(path, old_text, new_text)` replaces one exact text match.
- `create_file(path, content)` creates a new file without overwriting.
- `search_files(query, path)` searches text files in a workspace directory.

Tool paths are restricted to the configured workspace.

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
