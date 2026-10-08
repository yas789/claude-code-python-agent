# mlab terminal design

## Interaction

`mlab` launches from the current project. Its small cyan heading identifies the
agent, while muted workspace/provider/model metadata establishes context.
An editable `›` prompt follows a transcript that stays in terminal scrollback.

Answers use Markdown with syntax-highlighted code. Tool activity is two compact
lines: tool/arguments, then a bounded result receipt. Write payloads are summarized
by character count. A temporary spinner indicates model/tool activity; a footer
shows model, completed tools, tool errors, and elapsed time for the turn.

There is no alternate-screen application or fixed full-screen layout. Rich wraps
output to terminal width, and prompt_toolkit handles multiline editing and input
history. Quiet mode retains input and commands but removes welcome/progress/
footer decoration. Redirected one-shot output remains raw text.

## Responsibilities

| Module | Responsibility |
| --- | --- |
| `app/cli.py` | Console entry point, arguments, mode selection, exit codes |
| `app/settings.py` | Runtime local defaults, environment settings, API client |
| `app/chat.py` | Input/command/turn loop and expected-failure recovery |
| `app/input.py` | Editable prompt, completion, history, keyboard bindings |
| `app/terminal.py` | Rich welcome, answers, help, spinner, progress, footer |
| `app/commands.py` | Local slash-command catalog and dispatch |
| `app/session.py` | In-memory history and failed-turn protocol repair |
| `app/events.py` | Presentation-independent request/tool notifications |
| `app/failures.py` | Bounded, actionable expected-failure descriptions |
| `app/main.py` | Existing agent loop and workspace tool implementations |

The interactive session reuses the original agent loop with caller-owned history
and an optional event callback. Existing one-shot callers keep their original
defaults. A successful final answer is stored in history along with tool exchanges.
On failure, missing tool results are closed explicitly and completed results
remain. Cancellation does not undo filesystem operations already completed.

## Future skills and capabilities

- Add local commands to the shared command catalog and dispatch; help and input
  completion consume that catalog. Commands can later list/load actual skills.
- Add skill context to the session once there is a concrete skill loading format.
- Add token events for streaming while leaving tool receipt formatting reusable.
- Add session persistence with a versioned, normalized message format.
- Extract agent/tools from `app/main.py` when their next behavior change needs it.

These are extension points, not implemented skills, streaming, or saved sessions.
The current delivery checklist and verification history are in `PLAN.md`.
