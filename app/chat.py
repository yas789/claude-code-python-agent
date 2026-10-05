"""Interactive conversation control, separate from rendering and input."""


def chat(session, terminal, editor):
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
        with terminal.progress() as progress:
            answer = session.turn(prompt, on_event=progress)
        terminal.answer(answer)
        terminal.footer(session.model, progress)
