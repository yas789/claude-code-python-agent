import json
from pathlib import Path
from unittest.mock import patch

from app import main
from tests import helpers


class WriteToolTests(helpers.WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.file = self.root / "example.txt"
        self.file.write_text("hello world", encoding="utf-8")

    def test_edit_rejects_invalid_arguments_without_changing_file(self):
        cases = [
            ("path", None),
            ("path", False),
            ("path", ""),
            ("path", "bad\0path"),
            ("old_text", None),
            ("old_text", False),
            ("old_text", 1),
            ("old_text", ""),
            ("new_text", None),
            ("new_text", True),
            ("new_text", []),
        ]
        for name, value in cases:
            with self.subTest(argument=name, value=value):
                arguments = {"path": "example.txt", "old_text": "world", "new_text": "agent"}
                arguments[name] = value
                with self.assertRaisesRegex(RuntimeError, f"{name} must"):
                    self.tools.edit_file(**arguments)
                self.assertEqual(self.file.read_text(), "hello world")

    def test_edit_rejects_empty_target_in_empty_file(self):
        self.file.write_text("")
        with self.assertRaisesRegex(RuntimeError, "old_text must not be empty"):
            self.tools.edit_file("example.txt", "", "new")
        self.assertEqual(self.file.read_text(), "")

    def test_edit_rejects_unencodable_text_without_changing_file(self):
        original = self.file.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "edited content must be valid UTF-8 text"):
            self.tools.edit_file("example.txt", "world", "\ud800")
        self.assertEqual(self.file.read_bytes(), original)

    def test_agent_receives_edit_validation_error_without_mutation(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "invalid",
                            "edit_file",
                            '{"path": "example.txt", "old_text": "", "new_text": "new"}',
                        )
                    ],
                ),
                helpers.assistant_message("Choose a precise replacement target."),
            ]
        )
        self.run_agent(client, "Edit the file")
        self.assertEqual(
            helpers.tool_result(client.completions.calls[1]["messages"], "invalid")["content"],
            "error: old_text must not be empty",
        )
        self.assertEqual(self.file.read_text(), "hello world")

    def test_edit_receipt_is_compact_and_does_not_echo_content(self):
        replacement = "private text " * 10000
        result = self.tools.edit_file("./example.txt", "world", replacement)
        self.assertEqual(
            json.loads(result),
            {
                "status": "updated",
                "path": "example.txt",
                "replacements": 1,
            },
        )
        self.assertLess(len(result), 200)
        self.assertNotIn("private text", result)
        self.assertEqual(self.file.read_text(), "hello " + replacement)

    def test_edit_allows_deletion_and_unicode_replacement(self):
        self.tools.edit_file("example.txt", "world", "")
        self.assertEqual(self.file.read_text(), "hello ")
        result = json.loads(self.tools.edit_file("example.txt", "hello", "🙂終"))
        self.assertEqual(result["replacements"], 1)
        self.assertEqual(self.file.read_text(encoding="utf-8"), "🙂終 ")

    def test_agent_recovers_from_invalid_edit_and_receives_receipt(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "invalid",
                            "edit_file",
                            '{"path": "example.txt", "old_text": "", "new_text": "agent"}',
                        )
                    ],
                ),
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "valid",
                            "edit_file",
                            '{"path": "example.txt", "old_text": "world", "new_text": "agent"}',
                        )
                    ],
                ),
                helpers.assistant_message("Updated example.txt."),
            ]
        )
        self.assertEqual(self.run_agent(client, "Update the file"), "Updated example.txt.")
        receipt = json.loads(
            helpers.tool_result(client.completions.calls[2]["messages"], "valid")["content"]
        )
        self.assertEqual(receipt["status"], "updated")
        self.assertEqual(receipt["replacements"], 1)
        self.assertEqual(self.file.read_text(), "hello agent")

    def test_create_rejects_invalid_arguments_before_creating_file(self):
        cases = [
            ("path", None),
            ("path", False),
            ("path", ""),
            ("path", "bad\0path"),
            ("content", None),
            ("content", True),
            ("content", []),
            ("content", 1),
        ]
        for name, value in cases:
            with self.subTest(argument=name, value=value):
                arguments = {"path": "new.txt", "content": "new"}
                arguments[name] = value
                with self.assertRaisesRegex(RuntimeError, f"{name} must"):
                    self.tools.create_file(**arguments)
                self.assertFalse((self.root / "new.txt").exists())

    def test_create_rejects_unencodable_text_without_leaving_a_file(self):
        with self.assertRaisesRegex(RuntimeError, "content must be valid UTF-8 text"):
            self.tools.create_file("new.txt", "\ud800")
        self.assertFalse((self.root / "new.txt").exists())

    def test_create_writes_full_content_and_returns_compact_receipt(self):
        content = "🙂 private text\r\n" * 10000
        result = self.tools.create_file("./new.txt", content)
        self.assertEqual(
            json.loads(result),
            {
                "status": "created",
                "path": "new.txt",
                "chars_written": len(content),
            },
        )
        self.assertLess(len(result), 200)
        self.assertNotIn("private text", result)
        self.assertEqual((self.root / "new.txt").read_bytes(), content.encode("utf-8"))

    def test_create_allows_empty_content(self):
        receipt = json.loads(self.tools.create_file("empty.txt", ""))
        self.assertEqual(receipt["chars_written"], 0)
        self.assertEqual((self.root / "empty.txt").read_bytes(), b"")

    def test_create_does_not_overwrite_a_concurrently_created_file(self):
        original_open = open

        def concurrent_open(path, mode):
            Path(path).write_text("concurrent content")
            return original_open(path, mode)

        with patch.object(main, "open", side_effect=concurrent_open, create=True):
            with self.assertRaisesRegex(RuntimeError, "file already exists"):
                self.tools.create_file("new.txt", "agent content")
        self.assertEqual((self.root / "new.txt").read_text(), "concurrent content")

    def test_agent_recovers_from_invalid_creation_and_receives_receipt(self):
        client = helpers.FakeClient(
            [
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "invalid",
                            "create_file",
                            '{"path": "new.txt", "content": true}',
                        )
                    ],
                ),
                helpers.assistant_message(
                    None,
                    [
                        helpers.tool_call(
                            "valid",
                            "create_file",
                            '{"path": "new.txt", "content": "hello"}',
                        )
                    ],
                ),
                helpers.assistant_message("Created new.txt."),
            ]
        )
        self.assertEqual(self.run_agent(client, "Create a file"), "Created new.txt.")
        self.assertEqual(
            helpers.tool_result(client.completions.calls[1]["messages"], "invalid")["content"],
            "error: content must be a string",
        )
        result = json.loads(
            helpers.tool_result(client.completions.calls[2]["messages"], "valid")["content"]
        )
        self.assertEqual(result, {"status": "created", "path": "new.txt", "chars_written": 5})
        self.assertEqual((self.root / "new.txt").read_text(), "hello")
