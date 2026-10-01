import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import helpers
from app import main


class WriteToolTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.file = self.root / "example.txt"
        self.file.write_text("hello world", encoding="utf-8")
        workspace_patch = patch.object(main, "WORKSPACE_ROOT", self.root)
        workspace_patch.start()
        self.addCleanup(workspace_patch.stop)

    def test_edit_rejects_invalid_arguments_without_changing_file(self):
        cases = [
            ("path", None), ("path", False), ("path", ""), ("path", "bad\0path"),
            ("old_text", None), ("old_text", False), ("old_text", 1), ("old_text", ""),
            ("new_text", None), ("new_text", True), ("new_text", []),
        ]
        for name, value in cases:
            with self.subTest(argument=name, value=value):
                arguments = {"path": "example.txt", "old_text": "world", "new_text": "agent"}
                arguments[name] = value
                with self.assertRaisesRegex(RuntimeError, f"{name} must"):
                    main.edit_file(**arguments)
                self.assertEqual(self.file.read_text(), "hello world")

    def test_edit_rejects_empty_target_in_empty_file(self):
        self.file.write_text("")
        with self.assertRaisesRegex(RuntimeError, "old_text must not be empty"):
            main.edit_file("example.txt", "", "new")
        self.assertEqual(self.file.read_text(), "")

    def test_agent_receives_edit_validation_error_without_mutation(self):
        client = helpers.FakeClient([
            helpers.assistant_message(None, [helpers.tool_call(
                "invalid", "edit_file",
                '{"path": "example.txt", "old_text": "", "new_text": "new"}',
            )]),
            helpers.assistant_message("Choose a precise replacement target."),
        ])
        main.run_agent(client, "Edit the file")
        self.assertEqual(client.completions.calls[1]["messages"][2]["content"],
                         "error: old_text must not be empty")
        self.assertEqual(self.file.read_text(), "hello world")
