import json
import unittest

from app import main
from tests.helpers import WorkspaceTestCase


class ToolTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        (self.root / "README.md").write_text("# Claude Code Python Agent\n")
        (self.root / "app").mkdir()

    def test_read_file_can_read_workspace_file(self):
        self.assertIn("Claude Code Python Agent", self.tools.read_file("README.md"))

    def test_read_file_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            self.tools.read_file("../README.md")

    def test_read_file_rejects_directory_path(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a file"):
            self.tools.read_file(".")

    def test_list_files_lists_workspace_entries(self):
        files = json.loads(self.tools.list_files("."))["entries"]

        self.assertIn("README.md", files)
        self.assertIn("app", files)

    def test_list_files_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            self.tools.list_files("..")

    def test_list_files_rejects_file_path(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a directory"):
            self.tools.list_files("README.md")

    def test_edit_file_replaces_exact_text_once(self):
        file_path = self.root / "example.txt"
        file_path.write_text("hello world")
        result = self.tools.edit_file("example.txt", "world", "agent")

        self.assertEqual(
            json.loads(result),
            {
                "status": "updated",
                "path": "example.txt",
                "replacements": 1,
            },
        )
        self.assertEqual(file_path.read_text(), "hello agent")

    def test_edit_file_rejects_missing_old_text(self):
        file_path = self.root / "example.txt"
        file_path.write_text("hello world")
        with self.assertRaisesRegex(RuntimeError, "old_text not found"):
            self.tools.edit_file("example.txt", "missing", "agent")

    def test_edit_file_rejects_duplicate_old_text(self):
        file_path = self.root / "example.txt"
        file_path.write_text("hello hello")
        with self.assertRaisesRegex(RuntimeError, "old_text appears multiple times"):
            self.tools.edit_file("example.txt", "hello", "agent")

    def test_edit_file_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            self.tools.edit_file("../example.txt", "old", "new")

    def test_edit_file_rejects_directory_path(self):
        with self.assertRaisesRegex(RuntimeError, "path is not a file"):
            self.tools.edit_file(".", "old", "new")

    def test_create_file_writes_new_file(self):
        file_path = self.root / "created.txt"
        result = self.tools.create_file("created.txt", "hello agent")

        self.assertEqual(
            json.loads(result),
            {
                "status": "created",
                "path": "created.txt",
                "chars_written": 11,
            },
        )
        self.assertEqual(file_path.read_text(), "hello agent")

    def test_create_file_rejects_existing_file(self):
        file_path = self.root / "existing.txt"
        file_path.write_text("already here")
        with self.assertRaisesRegex(RuntimeError, "file already exists"):
            self.tools.create_file("existing.txt", "new content")

        self.assertEqual(file_path.read_text(), "already here")

    def test_create_file_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            self.tools.create_file("../created.txt", "hello")

    def test_create_file_rejects_missing_parent_directory(self):
        with self.assertRaisesRegex(RuntimeError, "parent directory does not exist"):
            self.tools.create_file("missing/created.txt", "hello")

    def test_search_files_returns_matching_lines(self):
        file_path = self.root / "example.txt"
        file_path.write_text("alpha\nbeta target\ngamma target")
        result = json.loads(self.tools.search_files("target", "."))["results"]

        self.assertEqual(
            result,
            [
                {
                    "path": "example.txt",
                    "line": 2,
                    "text": "beta target",
                    "text_truncated": False,
                },
                {
                    "path": "example.txt",
                    "line": 3,
                    "text": "gamma target",
                    "text_truncated": False,
                },
            ],
        )

    def test_search_files_returns_no_matches(self):
        file_path = self.root / "example.txt"
        file_path.write_text("alpha")
        self.assertEqual(json.loads(self.tools.search_files("missing", "."))["results"], [])

    def test_search_files_rejects_parent_directory_escape(self):
        with self.assertRaisesRegex(RuntimeError, "outside workspace"):
            self.tools.search_files("target", "..")

    def test_search_files_rejects_file_path(self):
        file_path = self.root / "example.txt"
        file_path.write_text("target")
        with self.assertRaisesRegex(RuntimeError, "path is not a directory"):
            self.tools.search_files("target", "example.txt")

    def test_search_files_ignores_configured_directories(self):
        ignored_path = self.root / "__pycache__"
        ignored_path.mkdir()
        (ignored_path / "ignored.txt").write_text("target")
        self.assertEqual(json.loads(self.tools.search_files("target", "."))["results"], [])

    def test_search_files_limits_results(self):
        for index in range(main.MAX_SEARCH_RESULTS + 5):
            file_path = self.root / f"example_{index}.txt"
            file_path.write_text("target")
        result = self.tools.search_files("target", ".")

        self.assertEqual(len(json.loads(result)["results"]), main.MAX_SEARCH_RESULTS)


if __name__ == "__main__":
    unittest.main()
