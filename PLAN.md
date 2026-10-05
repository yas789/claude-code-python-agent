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
- [~] 8. Display a spinner, tool progress, and turn statistics.
  Verification: captured progress output and success/error counts.
- [ ] 9. Add editable input, history, multiline entry, and command completion.
  Verification: prompt-toolkit pipe input tests and keyboard bindings.
- [ ] 10. Connect the interactive loop to sessions and presentation.
  Verification: two prompts and graceful EOF with a scripted model.
- [ ] 11. Add `/help`, `/new`, `/exit`, and unknown-command handling.
  Verification: command dispatch and context reset tests.
- [ ] 12. Add model inspection and switching with fresh context.
  Verification: model command tests and selected model in subsequent requests.
- [ ] 13. Show actionable errors and recover from Ctrl+C.
  Verification: connection/model/API failures and cancellation tests.
- [ ] 14. Keep one-shot and non-TTY output predictable.
  Verification: redirected output, quiet/verbose flags, and non-TTY startup tests.
- [ ] 15. Install `mlab` and verify a live Granite follow-up from another directory.
  Verification: editable tool installation, actual file tool, and remembered follow-up.
- [ ] 16. Document installation, appearance, controls, and extension points.
  Verification: full unittest suite, Ruff, package build, and final branch review.

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
