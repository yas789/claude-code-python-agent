import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from app import main
from app.errors import ToolError
from app.workspace import Workspace
from tests.helpers import FakeClient, WorkspaceTestCase, assistant_message, tool_call, tool_result


class WorkspaceTests(WorkspaceTestCase):
    def test_root_is_canonical_and_frozen(self):
        workspace = Workspace(self.root / ".." / self.root.name)
        self.assertEqual(workspace.root, self.root)
        with self.assertRaises(FrozenInstanceError):
            workspace.root = self.root.parent

    def test_resolution_rejects_escape_for_files_and_directories(self):
        for resolve, kind in (
            (self.tools.workspace.resolve_file, "file"),
            (self.tools.workspace.resolve_directory, "directory"),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(resolve("."), self.root)
                with self.assertRaisesRegex(ToolError, f"^{kind} is outside workspace"):
                    resolve("..")

    def test_interleaved_instances_keep_reads_writes_search_and_agents_isolated(self):
        with tempfile.TemporaryDirectory() as other_directory:
            other_root = Path(other_directory).resolve()
            other_tools = main.LocalTools(Workspace(other_root))
            other_registry = main.create_tool_registry(other_tools)
            for tools, content in ((self.tools, "first target"), (other_tools, "second target")):
                tools.create_file("shared.txt", content)
            self.tools.edit_file("shared.txt", "first", "updated")
            for tools, registry, expected in (
                (other_tools, other_registry, "second target"),
                (self.tools, self.registry, "updated target"),
                (other_tools, other_registry, "second target"),
            ):
                with self.subTest(root=tools.workspace.root, expected=expected):
                    self.assertEqual(json.loads(tools.read_file("shared.txt"))["content"], expected)
                    self.assertEqual(json.loads(tools.list_files("."))["entries"], ["shared.txt"])
                    results = json.loads(tools.search_files("target", "."))["results"]
                    self.assertEqual(results[0]["path"], "shared.txt")
                    self.assertEqual(results[0]["text"], expected)
                    client = FakeClient(
                        [
                            assistant_message(
                                None, [tool_call("read", "read_file", '{"path":"shared.txt"}')]
                            ),
                            assistant_message("Done"),
                        ]
                    )
                    self.assertEqual(main.run_agent(client, "read", tools=registry), "Done")
                    receipt = tool_result(client.completions.calls[1]["messages"], "read")
                    self.assertEqual(json.loads(receipt["content"])["content"], expected)

    def test_default_agent_workspace_is_computed_at_each_invocation(self):
        with tempfile.TemporaryDirectory() as other_directory:
            other_root = Path(other_directory).resolve()
            for root, expected in ((self.root, "first"), (other_root, "second")):
                (root / "shared.txt").write_text(expected, encoding="utf-8")
                client = FakeClient(
                    [
                        assistant_message(
                            None, [tool_call("read", "read_file", '{"path":"shared.txt"}')]
                        ),
                        assistant_message("Done"),
                    ]
                )
                with patch.object(Path, "cwd", return_value=root):
                    self.assertEqual(main.run_agent(client, "read"), "Done")
                receipt = tool_result(client.completions.calls[1]["messages"], "read")
                self.assertEqual(json.loads(receipt["content"])["content"], expected)


if __name__ == "__main__":
    unittest.main()
