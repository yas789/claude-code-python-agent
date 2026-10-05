import unittest
from threading import Timer

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from app.input import Input


class InputTests(unittest.TestCase):
    def test_enter_sends_and_alt_enter_inserts_newline(self):
        with create_pipe_input() as pipe:
            editor = Input(input=pipe, output=DummyOutput())
            pipe.send_text("first\x1b\rsecond\r")
            self.assertEqual(editor.read(), "first\nsecond")

    def test_history_up_recalls_previous_prompt(self):
        with create_pipe_input() as pipe:
            editor = Input(input=pipe, output=DummyOutput())
            pipe.send_text("remember this\r")
            self.assertEqual(editor.read(), "remember this")
            pipe.send_text("\x1b[A\r")
            self.assertEqual(editor.read(), "remember this")

    def test_tab_completes_slash_command(self):
        with create_pipe_input() as pipe:
            editor = Input(input=pipe, output=DummyOutput())
            pipe.send_text("/he\t")
            # Allow the completion task to run before sending Enter.
            enter = Timer(0.1, lambda: pipe.send_text("\r"))
            enter.start()
            try:
                self.assertEqual(editor.read(), "/help")
            finally:
                enter.join()

    def test_control_d_exits_and_control_c_interrupts(self):
        with create_pipe_input() as pipe:
            editor = Input(input=pipe, output=DummyOutput())
            pipe.send_text("\x04")
            with self.assertRaises(EOFError):
                editor.read()
            pipe.send_text("unfinished\x03")
            with self.assertRaises(KeyboardInterrupt):
                editor.read()
