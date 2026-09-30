# Long-Term Roadmap

## Goal

Grow this minimal coding agent into a reliable assistant that can complete the
full development loop:

**Understand → edit → run checks → fix failures → report results.**

The milestones below are planned work, not implemented capabilities. Complete
the reliable edit-and-test loop first; use evaluation results to guide later
investment in interactive sessions and larger-repository support.

## Current Architecture

`app/main.py` currently contains the CLI, OpenAI-compatible API integration,
tool schemas and implementations, workspace path checks, and agent loop.
The agent processes one prompt and executes tool calls sequentially until the
model returns an answer or the request limit is reached.

Available tools are `read_file`, `list_files`, `edit_file`, `create_file`, and
`search_files`. Tests use a fake model client and temporary workspaces to check
tool behavior and agent control flow.

## Milestone 1: Reliable Foundations

- [ ] Re-check resolved paths for each discovered search file so symlinks cannot
      bypass workspace containment.
- [ ] Validate tool argument shapes and types, returning actionable errors for
      malformed calls.
- [ ] Add line-range reads and bounded tool output with explicit truncation
      metadata.
- [ ] Distinguish tool rounds from model requests and allow a final summary when
      the tool budget is exhausted.
- [ ] Provide clear CLI errors for missing credentials, API failures, and
      exhausted budgets.
- [ ] Replace global workspace state with an explicit context passed to tools.

**Success criteria:** predictable, tested behavior for malformed calls, large
files, API failures, budget exhaustion, and paths outside the workspace.

## Milestone 2: Complete the Coding Loop

- [ ] Add command execution with an explicit working directory, timeouts,
      bounded output, and accurate exit codes.
- [ ] Define the command execution policy. A workspace working directory alone
      does not constrain a process's filesystem access.
- [ ] Add patch-based editing for precise changes across multiple locations.
- [ ] Add glob-based file discovery.
- [ ] Improve search with file filters, regex support, and configurable limits.
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
- [ ] Prune ignored directories before traversing them during search.
- [ ] Track token usage and cost information when the provider supplies it.
- [ ] Add configurable request and token budgets.
- [ ] Compact older history while preserving the task, key decisions, changed
      files, and verification results.

**Success criteria:** larger tasks stay within configured budgets and context
limits without losing essential task or verification evidence.

## Milestone 5: Interactive Experience

- [ ] Stream responses and display concise tool progress.
- [ ] Support interactive follow-up conversations.
- [ ] Save and resume sessions.
- [ ] Summarize changed files, checks run, and unresolved issues at completion.
- [ ] Define meaningful `--quiet` behavior and add structured output for scripts.

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
- [ ] Keep live-model evaluations opt-in and ordinary CI deterministic.

**Success criteria:** improvements are backed by repeatable task outcomes, not
only mocked control-flow tests or an expanding list of tools.

## Proposed Architecture

Extract responsibilities as the milestones introduce real changes, rather than
performing a large upfront refactor:

```text
app/
  main.py          # CLI entry point and output
  agent.py         # Model/tool loop, budgets, and recovery
  provider.py      # OpenAI-compatible API integration
  workspace.py     # Workspace context and path resolution
  tools/
    files.py       # Reads, creation, and patches
    search.py      # Discovery and content search
    commands.py    # Process execution and result capture
  session.py       # Conversation history and persistence
```

Keep tool schemas and their implementations aligned. The agent loop should
depend on explicit workspace/session context rather than module-level mutable
state. Separate provider calls from tool execution so both can be tested
independently.

## Recommended First Delivery

Build a **reliable edit-and-test loop**: foundation fixes, bounded reads, command
execution, focused agent instructions, and one meaningful end-to-end evaluation.
Use that milestone's results to prioritize the remaining roadmap.
