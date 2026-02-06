import unittest
from unittest.mock import patch

from tg_manager.core.config import ConfigError, load_settings
from tg_manager.core.security import AuthError, parse_bearer_token, verify_bearer_token


class TestConfig(unittest.TestCase):
    def test_load_settings_success_minimal(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "API_AUTH_TOKEN": "secret",
            },
            clear=True,
        ):
            settings = load_settings()
            self.assertEqual(settings.api_auth_token, "secret")
            self.assertEqual(settings.session_timeout_minutes, 10)
            self.assertEqual(settings.sqlite_path, "./data/tg_manager.sqlite3")

    def test_load_settings_missing_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                load_settings()
            self.assertIn("API_AUTH_TOKEN", str(ctx.exception))

    def test_load_settings_timeout_invalid_int(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "API_AUTH_TOKEN": "secret",
                "SESSION_TIMEOUT_MINUTES": "abc",
            },
            clear=True,
        ):
            with self.assertRaises(ConfigError) as ctx:
                load_settings()
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

