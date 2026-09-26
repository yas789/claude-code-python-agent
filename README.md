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

- `read_file(path)` reads a file inside the workspace.
- `list_files(path)` lists a directory inside the workspace.
- `edit_file(path, old_text, new_text)` replaces one exact text match.
- `create_file(path, content)` creates a new file without overwriting.
- `search_files(query, path)` searches text files in a workspace directory.

Tool paths are restricted to the configured workspace.

## Development

Run syntax checks:

```sh
python3 -m py_compile app/main.py
```

Run tests:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Branch Flow

- `main` is the stable branch.
- `dev` is the development integration branch.
- `feature/*` branches are used for focused changes.

GitHub Actions runs tests for pushes to `main`, `dev`, and `feature/**`, and for pull requests into `main` or `dev`.
