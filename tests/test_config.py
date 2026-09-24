import unittest
from unittest.mock import patch

from app import main

from tests.helpers import fixture_text


class ConfigTests(unittest.TestCase):
    def test_tool_loop_has_a_maximum_round_limit(self):
        self.assertGreater(main.MAX_TOOL_ROUNDS, 0)

    def test_create_client_requires_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY is not set"):
                main.create_client()

    def test_create_client_reads_api_key_at_runtime(self):
        calls = []

        def fake_openai(api_key, base_url):
            calls.append({"api_key": api_key, "base_url": base_url})
            return "client"

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True):
            with patch.object(main, "OpenAI", fake_openai):
                self.assertEqual(main.create_client(), "client")

        self.assertEqual(calls, [{"api_key": "test-key", "base_url": main.BASE_URL}])

    def test_fixture_text_reads_generated_answers(self):
        self.assertEqual(fixture_text("final_answer.txt"), "I can help with that.")

    def test_parse_args_accepts_prompt_alias(self):
        with patch("sys.argv", ["agent", "--prompt", "hello"]):
            args = main.parse_args()

        self.assertEqual(args.prompt, "hello")

    def test_parse_args_accepts_verbose_flag(self):
        with patch("sys.argv", ["agent", "--prompt", "hello", "--verbose"]):
            args = main.parse_args()

        self.assertTrue(args.verbose)

    def test_parse_args_accepts_quiet_flag(self):
        with patch("sys.argv", ["agent", "--prompt", "hello", "--quiet"]):
            args = main.parse_args()

        self.assertTrue(args.quiet)

    def test_parse_args_rejects_verbose_and_quiet_together(self):
        with patch("sys.argv", ["agent", "--prompt", "hello", "--verbose", "--quiet"]):
            with self.assertRaises(SystemExit):
                main.parse_args()

    def test_parse_args_accepts_max_tool_rounds(self):
        with patch("sys.argv", ["agent", "--prompt", "hello", "--max-tool-rounds", "3"]):
            args = main.parse_args()

        self.assertEqual(args.max_tool_rounds, 3)

    def test_parse_args_rejects_zero_max_tool_rounds(self):
        with patch("sys.argv", ["agent", "--prompt", "hello", "--max-tool-rounds", "0"]):
            with self.assertRaises(SystemExit):
                main.parse_args()


if __name__ == "__main__":
    unittest.main()
