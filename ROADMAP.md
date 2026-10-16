# Long-Term Roadmap

## Goal

Grow this minimal coding agent into a reliable assistant that can complete the
full development loop:

**Understand → edit → run checks → fix failures → report results.**

Unchecked items below are planned work; checked items are implemented. Complete
the reliable edit-and-test loop first; use evaluation results to guide later
investment in streaming, saved sessions, and larger-repository support.

## Current Architecture

There are two entry points sharing the same agent loop and five tools:

- `mlab` (`app/cli.py`) provides local Ollama defaults, interactive conversations
  or one-shot prompts, Markdown output, progress, and recoverable provider errors.
- `app.main` retains the legacy OpenRouter one-shot CLI; `your_program.sh` supplies
  local Ollama defaults, while `.codecrafters/run.sh` leaves provider settings to
  the caller. Both scripts use the checkout as the project/import root and keep
  the caller's working directory as the default workspace.

```text
app/cli.py ── chat.py ── session.py ──┐
           └─ one-shot ──────────────┤
app/main.py legacy CLI ──────────────┤
                                    ▼
                         main.py: run_agent
                                    │
                         registry.py: dispatch
                                    │
                         main.py: LocalTools
                                    │
                         workspace.py / writes.py
```

| Module | Current responsibility |
| --- | --- |
| `app/main.py` | Agent loop, SDK request helpers, `LocalTools`, search iterators, legacy CLI |
| `app/registry.py`, `app/schemas.py` | Schema/implementation registration, call parsing/binding, advertised tool contracts |
| `app/workspace.py`, `app/validation.py` | Explicit workspace containment and shared argument validation |
| `app/writes.py` | Atomic staged replacement for edits |
| `app/config.py`, `app/settings.py` | Static limits and runtime mlab provider settings |
| `app/session.py`, `app/chat.py`, `app/commands.py` | In-memory history, failed-turn repair, conversation and slash commands |
| `app/terminal.py`, `app/input.py` | Rich rendering and prompt-toolkit input |
| `app/events.py`, `app/diagnostics.py`, `app/failures.py` | Progress events, bounded tool summaries, provider failure messages |

Tools execute sequentially. The agent loop currently has no system instruction,
command runner, persistence, streaming, or context compaction. See
[TERMINAL_DESIGN.md](TERMINAL_DESIGN.md) for interaction details.

Available tools are `read_file`, `list_files`, `edit_file`, `create_file`, and
`search_files`. File reads support bounded line ranges; listing and search
support bounded pages with explicit continuation metadata. Search streams
matching text and checks discovered paths against the workspace. Write tools
validate argument types and return compact receipts. Edits pre-encode UTF-8 and
stage content before atomic replacement, preserving newline bytes and permission
bits. All successful tool results are JSON text; tool failures return `error: ...`.
Tests use scripted clients and temporary workspaces for tools and control flow,
plus terminal/launcher checks. CI is configured for locked dependencies, Ruff,
recursive syntax, unit tests, and an isolated wheel-install smoke check. The live
Ollama check remains opt-in. Delivery evidence is in [PLAN.md](PLAN.md).

## Milestone 1: Reliable Foundations

- [x] Re-check resolved paths for each discovered search file so symlinks cannot
      bypass workspace containment.
- [x] Validate tool argument shapes and types, returning actionable errors for
      malformed calls (`app/registry.py`, `app/validation.py`).
- [x] Add bounded line-range file reads with explicit truncation and continuation
      metadata. See [README.md](README.md#bounded-file-reads) for the contract and
      [FILE_READ_PLAN.md](FILE_READ_PLAN.md) for the verified implementation steps.
- [x] Bound successful listing/search output with explicit truncation metadata
      and return compact write receipts. See [WORKSPACE_TOOLS_PLAN.md](WORKSPACE_TOOLS_PLAN.md) for the verified
      implementation steps.
- [ ] Distinguish tool rounds from model requests and allow a final summary when
      the tool budget is exhausted.
- [x] Provide recoverable mlab errors for connection failures, missing models,
      timeouts, empty answers, and exhausted budgets (`app/failures.py`). Local
      defaults require no credential; remote authentication failures are reported.
- [ ] Bring the legacy CLI's failure handling to the same standard as mlab.
- [x] Replace global workspace state with an explicit context passed to tools
      (`Workspace`, instance-bound `LocalTools`, and injected registries).

Remaining foundation work also includes loading the legacy API URL at runtime
and narrowing tool exception handling so programming failures remain visible;
see [CLEAN_CODE.md](CLEAN_CODE.md). The current budget counts model requests and
can stop after a successful final tool round without a summary request.

**Success criteria:** predictable, tested behavior for malformed calls, large
files, API failures, budget exhaustion, and paths outside the workspace.

## Milestone 2: Complete the Coding Loop

- [ ] Add command execution with an explicit working directory, timeouts,
      bounded output, and accurate exit codes.
- [ ] Define the command execution policy. A workspace working directory alone
      does not constrain a process's filesystem access.
- [ ] Add patch-based editing for precise changes across multiple locations.
- [ ] Add glob-based file discovery.
- [ ] Improve search with file filters and regex support. Result/character limits
      and continuation offsets are already configurable.
- [ ] Add Git inspection so the agent can understand existing changes and
      summarize its edits.

**Success criteria:** the agent can reproduce a small bug, edit the relevant
code, run checks, recover from failures, and report the actual verification
result.

## Milestone 3: Better Agent Decisions

- [ ] Add focused system instructions: inspect before editing, follow repository
      conventions, verify changes, and distinguish evidence from assumptions.
- [ ] Load applicable `AGENTS.md` instructions from the workspace.
- [ ] Supply useful workspace context and project metadata.
- [ ] Improve recovery from tool errors and failed verification commands.
- [ ] Detect repeated identical failures and stop unproductive loops with a
      useful explanation.

**Success criteria:** representative coding tasks finish with relevant edits
and evidence-backed summaries rather than repeated tool failures or unverified
claims. Evaluate a single-agent implementation before adding orchestration.

## Milestone 4: Context and Cost Management

- [ ] Prefer targeted line-range reads over whole-file reads.
- [x] Prune ignored directories before traversing them during search.
- [ ] Track token usage and cost information when the provider supplies it.
- [ ] Add configurable request and token budgets.
- [ ] Compact older history while preserving the task, key decisions, changed
      files, and verification results.

**Success criteria:** larger tasks stay within configured budgets and context
limits without losing essential task or verification evidence.

## Milestone 5: Interactive Experience

- [ ] Stream responses.
- [x] Display concise tool progress in mlab.
- [x] Support interactive follow-up conversations in mlab.
- [ ] Save and resume sessions.
- [ ] Summarize changed files, checks run, and unresolved issues at completion.
- [x] Define meaningful `--quiet` behavior and plain one-shot output in mlab.
- [ ] Add structured output for scripts.

**Success criteria:** users can follow progress, continue a task, resume a
session, and consume predictable output interactively or from scripts.

## Milestone 6: Measured Quality

Begin evaluation alongside the first coding-loop milestone and expand it as
capabilities grow.

- [ ] Add an end-to-end fixture task that fixes a bug and verifies the result.
- [ ] Add a feature task against an existing fixture test suite.
- [ ] Evaluate recovery from failed edits and failed test commands.
- [ ] Evaluate code discovery in a larger directory tree.
- [ ] Track task success, verification success, model requests, token usage, and
      elapsed time.
- [x] Keep existing live-model checks opt-in and ordinary CI independent of models
      (`tests/live_mlab.py`). Full coding-task evaluations remain pending above.

**Success criteria:** improvements are backed by repeatable task outcomes, not
only mocked control-flow tests or an expanding list of tools.

## Proposed Architecture

The following is a possible future layout, not the current directory structure.
Extract responsibilities as the milestones introduce real changes, rather than
performing a large upfront refactor. Preserve the existing registry, validation,
settings, session, and presentation boundaries:

```text
app/
  cli.py           # mlab entry point (already exists)
  main.py          # Legacy entry point / compatibility
  agent.py         # Model/tool loop, budgets, and recovery
  provider.py      # OpenAI-compatible API integration
  workspace.py     # Workspace context and path resolution
  tools/
    files.py       # Reads, creation, and patches
    search.py      # Discovery and content search
    commands.py    # Process execution and result capture
  session.py       # Existing in-memory history; persistence remains future work
```

Keep tool schemas and their implementations aligned. The agent loop should
depend on explicit workspace/session context rather than module-level mutable
state. Separate provider calls from tool execution so both can be tested
independently.

## Recommended Next Delivery

After the consolidation milestone, fix tool-round budgeting so the last allowed
tool round can be followed by a final answer. Then build a **reliable edit-and-test
loop**: command execution with explicit policy, focused agent instructions, and
one meaningful end-to-end fixture evaluation. Existing bounded tools, injected
workspace context, sessions, and atomic edits provide the starting foundation.
Use actual task outcomes to prioritize streaming, persistence, and further tools.
