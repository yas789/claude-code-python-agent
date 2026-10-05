"""Local slash commands. These never go to the model."""

COMMANDS = {
    "/help": "Show commands and keyboard shortcuts",
    "/new": "Start a fresh conversation",
    "/model": "Show model; /model <name> switches with fresh context",
    "/exit": "Close mlab",
}


def dispatch(prompt, session, terminal):
    """Return True to exit, False to keep chatting."""
    parts = prompt.split(maxsplit=1)
    name = parts[0]
    argument = parts[1].strip() if len(parts) == 2 else ""
    if name not in COMMANDS:
        terminal.error(f"Unknown command: {name}. Use /help to see commands.")
    elif name == "/model":
        if not argument:
            terminal.notice(f"Current model: {session.model}")
        elif any(char.isspace() or ord(char) < 32 for char in argument):
            terminal.error("Use /model <name> with a single model name.")
        elif argument == session.model:
            terminal.notice(f"Already using {session.model}; conversation retained.")
        else:
            session.model = argument
            session.reset()
            terminal.notice(f"Switched to {argument}. Started a fresh conversation.")
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
