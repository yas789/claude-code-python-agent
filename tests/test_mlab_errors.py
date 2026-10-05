import unittest
from io import StringIO
from unittest.mock import patch

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.cli import main
from app.failures import describe_failure
from app.settings import LOCAL_BASE_URL, LOCAL_MODEL


class FailureTests(unittest.TestCase):
    def test_connection_and_timeout_hints(self):
        request = httpx.Request("POST", LOCAL_BASE_URL)
        message = describe_failure(APIConnectionError(request=request), LOCAL_BASE_URL, LOCAL_MODEL)
        self.assertIn("ollama serve", message)
        message = describe_failure(APITimeoutError(request=request), LOCAL_BASE_URL, LOCAL_MODEL)
        self.assertIn("timed out", message)

    def test_status_errors_do_not_dump_provider_payloads(self):
        for status, expected in [
            (404, "ollama pull"),
            (401, "MLAB_API_KEY"),
            (429, "rate-limited"),
            (400, "supports tools"),
            (500, "HTTP 500"),
        ]:
            response = httpx.Response(status, request=httpx.Request("POST", LOCAL_BASE_URL))
            error = APIStatusError("private payload", response=response, body=None)
            message = describe_failure(error, LOCAL_BASE_URL, LOCAL_MODEL)
            self.assertIn(expected, message)
            self.assertNotIn("private payload", message)

    def test_one_shot_errors_have_nonzero_exit_without_traceback(self):
        stderr = StringIO()
        with (
            patch("app.cli.run_agent", side_effect=RuntimeError("budget exhausted")),
            patch("sys.stderr", stderr),
        ):
            self.assertEqual(main(["--prompt", "hello"]), 1)
        self.assertIn("budget exhausted", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_one_shot_interrupt_returns_130(self):
        with (
            patch("app.cli.run_agent", side_effect=KeyboardInterrupt),
            patch("sys.stderr", StringIO()),
        ):
            self.assertEqual(main(["--prompt", "hello"]), 130)
