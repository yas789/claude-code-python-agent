# mlab terminal experience

## Goal

Launch `mlab` from any project for an attractive, scrollable conversation with
local Ollama (`granite3.3:2b`). Preserve the existing one-shot agent and tools.
Deliver this branch in at least 15 meaningful, verified commits.

## Starting state

- Branch: `feature/local-ollama`; clean working tree.
- Existing launcher defaults to Ollama Granite; the Python CLI is one-shot.
- Baseline: 170 unittest tests pass.
- No terminal rendering or editable-input dependencies yet.

## Checklist

- [x] 1. Record the delivery plan and verify the baseline.
  Verification: `uv run --locked python -m unittest discover -s tests -p 'test_*.py'`.
  Result: 170 tests passed.
- [x] 2. Package an installable `mlab` console command.
  Verification: build/install entry point and `uv run mlab --help`.
  Result: editable project built; entry point help and Ruff passed. Previous
  clean-code checklist archived in `CLEAN_CODE_PLAN.md`.
- [x] 3. Add local-first runtime configuration and one-shot arguments.
  Verification: configuration tests, including overrides and workspace validation.
  Result: four configuration tests, Ruff, and diff checks passed.
- [x] 4. Retain complete conversation history across successful turns.
  Verification: scripted follow-up includes prior answer and tool results.
  Result: 20 session/agent tests and Ruff passed; existing loop reused.
- [x] 5. Recover session history after failed or interrupted turns.
  Verification: API failure, interrupted tools, and budget-exhaustion tests.
  Result: five session tests passed; completed receipts retained and pending tool
  calls closed before retry. Ruff and diff checks passed.
- [x] 6. Emit bounded model/tool progress events independently of presentation.
  Verification: event order and tool-error tests plus existing agent tests.
  Result: 25 focused tests passed; progress hides write content and reports errors.
- [x] 7. Render welcome, Markdown answers, and concise metadata.
  Verification: narrow-terminal and plain-output rendering checks.
  Result: two rendering tests passed at 36 columns; no ANSI in plain output.
- [x] 8. Display a spinner, tool progress, and turn statistics.
  Verification: captured progress output and success/error counts.
  Result: three rendering/progress tests passed; spinner confined to TTY output.
- [x] 9. Add editable input, history, multiline entry, and command completion.
  Verification: prompt-toolkit pipe input tests and keyboard bindings.
  Result: four real pipe-input tests passed (including asynchronous completion).
- [x] 10. Connect the interactive loop to sessions and presentation.
  Verification: two prompts and graceful EOF with a scripted model.
  Result: seven chat/session tests passed; blank input and input Ctrl+C make no requests.
- [x] 11. Add `/help`, `/new`, `/exit`, and unknown-command handling.
  Verification: command dispatch and context reset tests.
  Result: 11 chat/input/rendering tests passed; commands never call the model.
- [x] 12. Add model inspection and switching with fresh context.
  Verification: model command tests and selected model in subsequent requests.
  Result: ten chat/input tests passed; invalid/same model preserves context.
- [x] 13. Show actionable errors and recover from Ctrl+C.
  Verification: connection/model/API failures and cancellation tests.
  Result: 20 focused tests passed; bounded timeout, actionable provider errors,
  cancellation recovery, and one-shot exit codes verified.
- [x] 14. Keep one-shot and non-TTY output predictable.
  Verification: redirected output, quiet/verbose flags, and non-TTY startup tests.
  Result: 11 CLI/rendering/error tests passed; plain stdout, verbose stderr,
  quiet presentation, and early non-TTY guidance verified.
- [x] 15. Install `mlab` and verify a live Granite follow-up from another directory.
  Verification: editable tool installation, actual file tool, and remembered follow-up.
  Result: installed `~/.local/bin/mlab`; real Granite file read and remembered
  follow-up passed with temperature 0. Four CLI tests include actual PTY startup,
  /help and /exit from another directory. OpenAI SDK bounded to tested major 2.
- [x] 16. Document installation, appearance, controls, and extension points.
  Verification: full unittest suite, Ruff, package build, and final branch review.
  Result: 206 tests passed; Ruff lint/format and diff checks clean; sdist and
  wheel built. README/design/roadmap updated. Final audit extended empty-answer
  error handling to one-shot mode and disabled input colors with NO_COLOR.

## Design

- Small cyan `mlab` heading; muted workspace/model metadata; Markdown responses.
- Append-only transcript with native terminal scrollback, compact tool receipts.
- Rich for rendering and status; prompt_toolkit for input and completion.
- Enter sends; Alt+Enter inserts a newline; Ctrl+C cancels/clears; Ctrl+D exits.
- Sessions remain in memory. Future skills can use slash-command dispatch and
  progress events; streaming and persistence are later features.
- Introduce modules only as the corresponding layer needs them.

## Verification notes

Live model checks are opt-in; automated tests use scripted clients. Each step
is verified before proceeding. Cancellation does not undo completed file edits.

Step 15 investigation: Granite intermittently returned empty follow-up answers;
Qwen was tried at the user's request but emitted tool JSON as ordinary text.
Retain Granite unless Qwen passes actual tool execution. Verify deterministic
generation and report empty answers as recoverable failures before completing.
Resolved: deterministic Granite generation passed the live check. Qwen did not
pass native tool execution, so the default remains Granite.

## Edit reliability: five-commit delivery

Goal: prevent failed edits from truncating files, with five narrow verified commits.
Starting state: editing writes directly to the destination without pre-encoding;
the terminal milestone above is complete. Preserve the existing tool receipt.

- [x] 1. Pre-encode edited content and reject invalid UTF-8 before mutation.
  Verification: reproduce the surrogate regression; run write-tool tests.
  Result: regression reproduced before the fix; 13 write-tool tests and Ruff
  lint/format/diff checks passed after pre-encoding.
- [x] 2. Stage edits beside the destination and replace atomically.
  Verification: inject staging-write and replacement failures; verify original bytes.
  Result: all 15 write-tool tests passed, including partial-write and replacement
  failures with staging cleanup. Ruff lint/format/diff checks passed.
- [x] 3. Preserve newline bytes and permission bits across replacements.
  Verification: CRLF/mixed-newline, executable-mode, and symlink-target tests.
  Result: 23 write-tool/workspace tests passed; exact multiline matching, unchanged
  newline bytes, permissions, and resolved symlink targets verified. Ruff and diff
  checks passed.
- [x] 4. Verify interruption cleanup and agent recovery from failed edits.
  Verification: cancellation and scripted model recovery tests.
  Result: 47 write-tool/session/agent tests passed. Invalid UTF-8 supports a valid
  retry; failed replacement remains readable; cancellation before replacement
  preserves the original, while cancellation after replacement retains the edit
  and permits a follow-up inspection. Staging cleanup, Ruff, and diff checks passed.
- [x] 5. Document guarantees and complete the audit.
  Verification: full unittest suite, Ruff lint/format, and diff checks.
  Result: all 217 tests passed under `uv run --locked`; Ruff lint/format and diff
  checks passed. README documents exact newline matching, atomic commit boundaries,
  permissions, symlinks, and replacement semantics. The encoding finding is closed
  in `CLEAN_CODE.md`; the partial refactor plan records this focused delivery.

Each completed step is one commit; update results before starting the next step.

## Consolidation: ten-commit delivery

Goal: establish a freshly verified baseline, reproducible CI, working launchers
and packaging, accurate documentation, and an evidence-backed integration path.

Starting state: `feature/consolidate-current-work` branches from
`feature/local-ollama` at `ae0adb3`. The only untracked file is user-owned
`hello.txt`; it is excluded from this delivery. Prior delivery records above are
historical evidence, not fresh verification. Use one verified commit per step.

- [x] 1. Record this plan and verify the baseline.
  Verification: full unittest suite, Ruff lint/format, and `git diff --check`.
  Result: all 217 tests passed; Ruff lint and formatting (41 files), and diff
  checks passed. No baseline failures. Starting tracked tree was clean.
- [x] 2. Use locked runtime/development dependencies in CI.
  Verification: inspect workflow structure; run its locked sync and test commands.
  Result: CI pins uv 0.12.19 (the locally verified version), syncs the lockfile
  including development dependencies, and runs checks with uv. Sync, syntax,
  all 217 tests, and diff checks passed. Workflow structure manually reviewed;
  actionlint is unavailable locally. GitHub-hosted execution awaits a push.
- [x] 3. Enforce existing Ruff lint and formatting standards in CI.
  Verification: run both locked Ruff commands and inspect workflow steps.
  Result: named lint and formatting CI steps use the existing configuration;
  both commands passed (41 formatted files), with clean diff checks.
- [x] 4. Check syntax across application and test modules.
  Verification: `uv run --locked python -m compileall -q app tests`.
  Result: recursive syntax check passed; CI and README now use the same command.
  Diff checks passed.
- [x] 5. Correct launcher project roots and verify external-directory use.
  Verification: focused launcher regressions without provider requests.
  Result: reproduced the remote launcher's `.codecrafters` root error before
  fixing it. Both launchers now use absolute checkout roots without changing the
  caller's working directory. Four regressions passed, covering spaces in paths,
  provider defaults/overrides, forwarded arguments, and real external-directory
  help. Ruff lint/format (42 files) and diff checks passed after formatting the
  new test module.
- [x] 6. Verify an isolated wheel installation and entry point in CI.
  Verification: build wheel, install in a fresh environment, run help and non-TTY
  startup outside the checkout with checkout import paths removed.
  Result: `tests/package_smoke.py` passed: built a fresh wheel, installed hashed
  locked runtime requirements and the wheel into a temporary venv, checked
  dependency compatibility and import location, and verified installed help and
  exit code 2 on non-TTY startup from an unrelated directory. No provider calls.
  CI runs the same script; Ruff lint/format (43 files) and diff checks passed.
- [x] 7. Reconcile clean-code findings and partial delivery status.
  Verification: audit changed claims against implementation and focused tests.
  Result: updated current dispositions with source/test evidence and preserved
  historical delivery records. Explicitly retained incomplete extraction,
  legacy import-time configuration, annotations, and broad tool exception
  handling as open work. All 109 focused tests and diff checks passed.
- [x] 8. Refresh architecture and roadmap status.
  Verification: cross-check changed module descriptions and milestone checkboxes.
  Result: documented both entry points, actual modules and call flow, atomic
  edits, validation, injected workspace state, and model-independent CI. Pending
  budgeting, execution, legacy errors, and extraction remain explicit. Compared
  claims with implementation and ran all 34 focused registry/workspace/session/
  configuration/error tests; diff checks passed.
- [x] 9. Align contributor documentation with actual local and CI checks.
  Verification: exercise deterministic documented commands and check local links.
  Result: README lists the exact CI sequence, uv version, launcher distinctions,
  packaging isolation/build requirements, and separate opt-in live verification.
  Ran the documented sequence: locked sync, Ruff lint/format (43 files), recursive
  syntax, all 221 tests, and isolated wheel smoke passed. Local Markdown link
  targets and the bounded-read anchor were inspected; diff checks passed.
  Live Ollama was not run during consolidation.
- [ ] 10. Record final audit and integration readiness.
  Verification: full tests, Ruff lint/format, syntax, packaging smoke, diff review,
  and refreshed remote branch relationships. Record any unavailable checks.

Execution: mark exactly one item in progress, verify it, record its result, and
commit only intended files before starting the next item. Stop on unresolved
verification failures. Record substantial scope changes before implementing them.
Live Ollama checks remain opt-in. Branch integration follows final graph review.
