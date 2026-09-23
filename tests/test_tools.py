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

    def test_create_file_writes_new_file(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "created.txt"

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                result = main.create_file("created.txt", "hello agent")

            self.assertEqual(result, "created created.txt")
            self.assertEqual(file_path.read_text(), "hello agent")

    def test_create_file_rejects_existing_file(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "existing.txt"
            file_path.write_text("already here")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "file already exists"):
                    main.create_file("existing.txt", "new content")

            self.assertEqual(file_path.read_text(), "already here")

    def test_create_file_rejects_parent_directory_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "outside workspace"):
                    main.create_file("../created.txt", "hello")

    def test_create_file_rejects_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "parent directory does not exist"):
                    main.create_file("missing/created.txt", "hello")

    def test_search_files_returns_matching_lines(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("alpha\nbeta target\ngamma target")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                result = main.search_files("target", ".")

            self.assertIn("example.txt:2: beta target", result)
            self.assertIn("example.txt:3: gamma target", result)

    def test_search_files_returns_no_matches(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("alpha")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                self.assertEqual(main.search_files("missing", "."), "no matches")

    def test_search_files_rejects_parent_directory_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "outside workspace"):
                    main.search_files("target", "..")

    def test_search_files_rejects_file_path(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = Path(workspace) / "example.txt"
            file_path.write_text("target")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                with self.assertRaisesRegex(RuntimeError, "path is not a directory"):
                    main.search_files("target", "example.txt")

    def test_search_files_ignores_configured_directories(self):
        with tempfile.TemporaryDirectory() as workspace:
            ignored_path = Path(workspace) / "__pycache__"
            ignored_path.mkdir()
            (ignored_path / "ignored.txt").write_text("target")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                self.assertEqual(main.search_files("target", "."), "no matches")

    def test_search_files_limits_results(self):
        with tempfile.TemporaryDirectory() as workspace:
            for index in range(main.MAX_SEARCH_RESULTS + 5):
                file_path = Path(workspace) / f"example_{index}.txt"
                file_path.write_text("target")

            with patch.object(main, "WORKSPACE_ROOT", Path(workspace)):
                result = main.search_files("target", ".")

            self.assertEqual(len(result.splitlines()), main.MAX_SEARCH_RESULTS)


if __name__ == "__main__":
    unittest.main()
