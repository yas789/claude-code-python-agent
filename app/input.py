"""Editable, multiline terminal input with in-memory history."""

import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from app.commands import COMMANDS


class Input:
    def __init__(self, *, input=None, output=None):
        bindings = KeyBindings()

        @bindings.add("enter")
        def send(event):
            event.current_buffer.validate_and_handle()

        @bindings.add("escape", "enter")
        def newline(event):
            event.current_buffer.insert_text("\n")

        self.session = PromptSession(
            history=InMemoryHistory(),
            completer=WordCompleter(list(COMMANDS), sentence=True),
            complete_while_typing=False,
            multiline=True,
            key_bindings=bindings,
            style=Style.from_dict({"prompt": "bold ansicyan"})
            if "NO_COLOR" not in os.environ
            else None,
            input=input,
            output=output,
        )

    def read(self):
        return self.session.prompt(
            FormattedText([("class:prompt", "› ")]), prompt_continuation="  "
        )
