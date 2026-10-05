"""Local slash commands. These never go to the model."""

COMMANDS = {
    "/help": "Show commands and keyboard shortcuts",
    "/new": "Start a fresh conversation",
    "/exit": "Close mlab",
}


def dispatch(prompt, session, terminal):
    """Return True to exit, False to keep chatting."""
    name, _, argument = prompt.partition(" ")
    if name not in COMMANDS:
        terminal.error(f"Unknown command: {name}. Use /help to see commands.")
    elif argument.strip():
        terminal.error(f"{name} does not accept arguments.")
    elif name == "/help":
        terminal.help(COMMANDS)
    elif name == "/new":
        session.reset()
        terminal.notice("Started a fresh conversation.")
    elif name == "/exit":
        terminal.notice("Goodbye.")
        return True
    return False
