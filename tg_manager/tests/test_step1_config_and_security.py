import unittest

from tg_manager.core.config import ConfigError, load_settings
from tg_manager.core.security import AuthError, parse_bearer_token, verify_bearer_token


class TestConfig(unittest.TestCase):
    def test_load_settings_success_minimal(self) -> None:
        settings = load_settings(
            environ={
                "API_AUTH_TOKEN": "secret",
            }
        )
        self.assertEqual(settings.api_auth_token, "secret")
        self.assertEqual(settings.session_timeout_minutes, 10)
        self.assertEqual(settings.sqlite_path, "./db/contextswap.sqlite3")
        self.assertEqual(settings.delegation_market_slug, "will-donald-trump-win-the-2028-us-presidential-election")
        self.assertEqual(settings.delegation_question_dir, "~/.openclaw/question")
        self.assertEqual(settings.delegation_wait_seconds, 120)
        self.assertFalse(settings.mock_bots_enabled)
        self.assertTrue(settings.mock_seller_auto_end)

    def test_load_settings_missing_required(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            load_settings(environ={})
        self.assertIn("API_AUTH_TOKEN", str(ctx.exception))

    def test_load_settings_timeout_invalid_int(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            load_settings(
                environ={
                    "API_AUTH_TOKEN": "secret",
                    "SESSION_TIMEOUT_MINUTES": "abc",
                }
            )
        self.assertIn("SESSION_TIMEOUT_MINUTES", str(ctx.exception))


class TestSecurity(unittest.TestCase):
    def test_parse_bearer_token(self) -> None:
        self.assertEqual(parse_bearer_token("Bearer a1"), "a1")
        self.assertEqual(parse_bearer_token("Bearer   a1  "), "a1")
        self.assertIsNone(parse_bearer_token(None))
        self.assertIsNone(parse_bearer_token(""))
        self.assertIsNone(parse_bearer_token("Basic abc"))
        self.assertIsNone(parse_bearer_token("Bearer"))

    def test_verify_bearer_token(self) -> None:
        verify_bearer_token("Bearer x", expected_token="x")
        with self.assertRaises(AuthError):
            verify_bearer_token(None, expected_token="x")
        with self.assertRaises(AuthError):
            verify_bearer_token("Bearer y", expected_token="x")


if __name__ == "__main__":
    unittest.main()
