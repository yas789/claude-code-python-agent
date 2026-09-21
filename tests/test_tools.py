import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main


class ToolTests(unittest.TestCase):
    def test_read_file_can_read_workspace_file(self):
        self.assertIn("Build Your own Claude Code", main.read_file("README.md"))

    def test_read_file_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            main.read_file("../README.md")

    def test_read_file_rejects_directory_path(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a file"):
            main.read_file(".")

    def test_list_files_lists_workspace_entries(self):
        files = main.list_files(".")

        self.assertIn("README.md", files)
        self.assertIn("app", files)

    def test_list_files_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            main.list_files("..")

    def test_list_files_rejects_file_path(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a directory"):
            main.list_files("README.md")

    def test_edit_file_replaces_exact_text_once(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello world")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                result = main.edit_file("example.txt", "world", "agent")

            self.assertEqual(result, "updated example.txt")
            self.assertEqual(file_path.read_text(), "hello agent")

    def test_edit_file_rejects_missing_old_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello world")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "old_text not found"):
                    main.edit_file("example.txt", "missing", "agent")

    def test_edit_file_rejects_duplicate_old_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("hello hello")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "old_text appears multiple times"):
                    main.edit_file("example.txt", "hello", "agent")

    def test_edit_file_rejects_parent_directory_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "outside workspace"):
                    main.edit_file("../example.txt", "old", "new")

    def test_edit_file_rejects_directory_path(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "path is not a file"):
                    main.edit_file(".", "old", "new")


if __name__ == "__main__":
    unittest.main()
