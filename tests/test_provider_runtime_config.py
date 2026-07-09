"""
tests/test_provider_runtime_config.py

Sprint 3, Task 3 — covers ONLY the four new ProviderConfig fields added to
core/config.py (active_provider, model, timeout_seconds, temperature).

Kept as a separate file from the project's existing tests/test_config.py so
this task's diff never touches a test file it did not create — existing
config tests are left completely alone.
"""

from __future__ import annotations

import os
import unittest

from core.config import ConfigError, get_config

_ENV_KEYS = (
    "ACTIVE_PROVIDER",
    "MODEL_NAME",
    "PROVIDER_TIMEOUT_SECONDS",
    "TEMPERATURE",
    "OPENAI_API_KEY",
)


class _EnvIsolatedTestCase(unittest.TestCase):
    """Snapshots and restores the relevant env vars; clears the Config cache."""

    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        get_config.cache_clear()

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_config.cache_clear()


class TestDefaults(_EnvIsolatedTestCase):
    def test_defaults_when_unset(self):
        config = get_config()
        self.assertEqual(config.providers.active_provider, "openai")
        # Updated to match the new default model gpt-5.5
        self.assertEqual(config.providers.model, "gpt-5.5")
        self.assertEqual(config.providers.timeout_seconds, 30.0)
        self.assertEqual(config.providers.temperature, 0.7)


class TestEnvOverrides(_EnvIsolatedTestCase):
    def test_active_provider_read_and_lowercased(self):
        os.environ["ACTIVE_PROVIDER"] = "Claude"
        config = get_config()
        self.assertEqual(config.providers.active_provider, "claude")

    def test_model_name_read(self):
        os.environ["MODEL_NAME"] = "gpt-4o-mini"
        config = get_config()
        self.assertEqual(config.providers.model, "gpt-4o-mini")

    def test_timeout_seconds_read(self):
        os.environ["PROVIDER_TIMEOUT_SECONDS"] = "45"
        config = get_config()
        self.assertEqual(config.providers.timeout_seconds, 45.0)

    def test_temperature_read(self):
        os.environ["TEMPERATURE"] = "1.2"
        config = get_config()
        self.assertEqual(config.providers.temperature, 1.2)


class TestInvalidNumericValues(_EnvIsolatedTestCase):
    def test_non_numeric_timeout_raises_config_error(self):
        os.environ["PROVIDER_TIMEOUT_SECONDS"] = "not-a-number"
        with self.assertRaises(ConfigError):
            get_config()

    def test_non_numeric_temperature_raises_config_error(self):
        os.environ["TEMPERATURE"] = "hot"
        with self.assertRaises(ConfigError):
            get_config()


if __name__ == "__main__":
    unittest.main()
