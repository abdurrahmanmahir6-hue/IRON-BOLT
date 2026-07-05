"""
tests/test_config.py

Covers core/config.py:
    - Config.load() reads environment variables correctly.
    - Config.load() falls back to sane defaults when env vars are unset.
    - masked_summary() never leaks raw secret values.
    - validate(strict=True) raises ConfigError with no provider keys,
      and passes once at least one key is present.
    - validate(strict=False) (the Sprint 2 default) never raises.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from core.config import Config, ConfigError

# Point at a path that can never exist, so Config.load()'s internal
# load_dotenv() call never picks up a real .env file and leaks values
# into these tests.
_NO_DOTENV_PATH = "/nonexistent/this-file-does-not-exist/.env"


class TestConfigLoad(unittest.TestCase):
    def test_load_uses_defaults_when_env_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(dotenv_path=_NO_DOTENV_PATH)

        self.assertEqual(config.app_name, "Mahir AI OS")
        self.assertEqual(config.app_version, "AR1")
        self.assertEqual(config.environment, "development")
        self.assertEqual(config.log_level, "INFO")
        self.assertIsNone(config.openai_api_key)
        self.assertIsNone(config.gemini_api_key)
        self.assertIsNone(config.tavily_api_key)

    def test_load_reads_environment_variables(self) -> None:
        env = {
            "APP_NAME": "Test OS",
            "APP_VERSION": "AR2",
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "OPENAI_API_KEY": "sk-fake-openai-key",
            "GEMINI_API_KEY": "fake-gemini-key",
            "TAVILY_API_KEY": "fake-tavily-key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.load(dotenv_path=_NO_DOTENV_PATH)

        self.assertEqual(config.app_name, "Test OS")
        self.assertEqual(config.app_version, "AR2")
        self.assertEqual(config.environment, "production")
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.openai_api_key, "sk-fake-openai-key")
        self.assertEqual(config.gemini_api_key, "fake-gemini-key")
        self.assertEqual(config.tavily_api_key, "fake-tavily-key")


class TestConfigMaskedSummary(unittest.TestCase):
    def test_masked_summary_never_leaks_secret_values(self) -> None:
        config = Config(openai_api_key="sk-super-secret-value")
        summary = str(config.masked_summary())

        self.assertNotIn("sk-super-secret-value", summary)
        self.assertIn("set (", config.masked_summary()["openai_api_key"])

    def test_masked_summary_reports_not_set(self) -> None:
        config = Config(openai_api_key=None)
        self.assertEqual(config.masked_summary()["openai_api_key"], "not set")


class TestConfigValidate(unittest.TestCase):
    def test_strict_raises_without_any_provider_key(self) -> None:
        config = Config()
        with self.assertRaises(ConfigError):
            config.validate(strict=True)

    def test_strict_passes_with_one_provider_key(self) -> None:
        config = Config(openai_api_key="sk-fake")
        config.validate(strict=True)  # must not raise

    def test_non_strict_never_raises(self) -> None:
        config = Config()
        config.validate(strict=False)  # must not raise, even with no keys


if __name__ == "__main__":
    unittest.main()
