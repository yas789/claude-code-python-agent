import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = ("your_program.sh", ".codecrafters/run.sh")


class LauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.checkout = self.root / "checkout with spaces"
        self.caller = self.root / "caller project"
        self.bin = self.root / "bin"
        self.caller.mkdir()
        self.bin.mkdir()
        for name in LAUNCHERS:
            destination = self.checkout / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        recorder = self.root / "record.py"
        recorder.write_text(
            "import json, os, sys\n"
            "print(json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd(), "
            "'env': dict(os.environ)}))\n"
        )
        uv = self.bin / "uv"
        uv.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(recorder))} "$@"\n'
        )
        uv.chmod(0o755)
        self.env = {
            key: value for key, value in os.environ.items() if not key.startswith("OPENROUTER_")
        }
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]

    def capture(self, launcher, **overrides):
        result = subprocess.run(
            [str(self.checkout / launcher), "--prompt", "inspect this project"],
            cwd=self.caller,
            env={**self.env, **overrides},
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return json.loads(result.stdout)

    def test_launchers_select_checkout_and_preserve_caller_workspace(self):
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher):
                captured = self.capture(launcher)
                args = captured["args"]
                self.assertEqual(args[args.index("--project") + 1], str(self.checkout))
                self.assertEqual(captured["env"]["PYTHONPATH"], str(self.checkout))
                self.assertEqual(captured["env"]["PYTHONSAFEPATH"], "1")
                self.assertEqual(captured["cwd"], str(self.caller))
                self.assertEqual(args[-2:], ["--prompt", "inspect this project"])
                self.assertEqual(args[args.index("-m") + 1], "app.main")

    def test_local_launcher_defaults_and_provider_overrides(self):
        captured = self.capture("your_program.sh")
        self.assertEqual(captured["env"]["OPENROUTER_BASE_URL"], "http://localhost:11434/v1")
        self.assertEqual(captured["env"]["OPENROUTER_API_KEY"], "ollama")
        self.assertEqual(captured["args"][captured["args"].index("--model") + 1], "granite3.3:2b")
        overrides = {"OPENROUTER_BASE_URL": "https://example.test/v1", "OPENROUTER_API_KEY": "test"}
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher):
                captured = self.capture(launcher, **overrides)
                for key, value in overrides.items():
                    self.assertEqual(captured["env"][key], value)

    def test_remote_launcher_leaves_provider_configuration_to_caller(self):
        captured = self.capture(".codecrafters/run.sh")
        self.assertNotIn("OPENROUTER_BASE_URL", captured["env"])
        self.assertNotIn("OPENROUTER_API_KEY", captured["env"])
        self.assertNotIn("--model", captured["args"])

    def test_real_launchers_show_help_outside_checkout(self):
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher):
                result = subprocess.run(
                    [str(ROOT / launcher), "--help"],
                    cwd=self.caller,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--workspace", result.stdout)
                self.assertIn("--prompt", result.stdout)
                self.assertNotIn("Traceback", result.stderr)
