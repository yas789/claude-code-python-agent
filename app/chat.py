"""Interactive conversation control, separate from rendering and input."""

from openai import APIError

from app.commands import dispatch
from app.failures import describe_failure


def chat(session, terminal, editor, *, base_url="http://localhost:11434/v1"):
    while True:
        try:
            prompt = editor.read().strip()
        except EOFError:
            terminal.notice("Goodbye.")
            return 0
        except KeyboardInterrupt:
            continue
        if not prompt:
            continue
        if prompt.startswith("/"):
            if dispatch(prompt, session, terminal):
                return 0
            continue
        try:
            with terminal.progress() as progress:
                answer = session.turn(prompt, on_event=progress)
        except KeyboardInterrupt:
            terminal.notice("Cancelled. Completed file changes remain.")
            continue
        except (APIError, RuntimeError) as error:
            terminal.error(describe_failure(error, base_url, session.model))
            continue
        terminal.answer(answer)
        terminal.footer(session.model, progress)
