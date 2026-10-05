import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from app.cli import parse_args
from app.settings import LOCAL_BASE_URL, LOCAL_MODEL, Settings


class MlabConfigTests(unittest.TestCase):
    def test_local_defaults_need_no_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings.from_env()
            args = parse_args([])
        self.assertEqual(settings, Settings(LOCAL_BASE_URL, "ollama", LOCAL_MODEL))
        self.assertIsNone(args.prompt)
        self.assertEqual(args.workspace, Path.cwd().resolve())

    def test_environment_and_arguments_override_defaults(self):
        with patch.dict(
            "os.environ",
            {
                "MLAB_MODEL": "env-model",
                "MLAB_BASE_URL": "http://localhost:9999/v1",
                "MLAB_API_KEY": "test-key",
                "OPENROUTER_API_KEY": "legacy-key",
            },
            clear=True,
        ):
            self.assertEqual(Settings.from_env().api_key, "test-key")
            self.assertEqual(parse_args([]).model, "env-model")
            args = parse_args(["--model", "cli-model", "--base-url", LOCAL_BASE_URL])
        self.assertEqual(args.model, "cli-model")
        self.assertEqual(args.base_url, LOCAL_BASE_URL)

    def test_invalid_arguments_fail_before_connecting(self):
        for argv in (
            ["--workspace", "/nonexistent-mlab-workspace"],
            ["--max-tool-rounds", "0"],
            ["--model", " "],
            ["--prompt", " "],
            ["--quiet", "--verbose"],
        ):
            with self.subTest(argv=argv), patch("sys.stderr", StringIO()):
                with self.assertRaises(SystemExit) as error:
                    parse_args(argv)
                self.assertEqual(error.exception.code, 2)

    def test_provider_has_bounded_timeout_and_no_automatic_retries(self):
        with patch("app.settings.OpenAI") as create:
            Settings(LOCAL_BASE_URL, "ollama", LOCAL_MODEL).create_client()
        create.assert_called_once_with(
            base_url=LOCAL_BASE_URL, api_key="ollama", timeout=120.0, max_retries=0
        )
