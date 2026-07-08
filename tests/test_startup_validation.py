"""
tests/test_startup_validation.py

Sprint 3, Task 3 — Environment Validation tests.

Each subsection dataclass in core/config.py is independently constructible
(per its own docstring contract), so these tests build Config/ProviderConfig
objects directly rather than going through environment variables — faster,
and immune to whatever is or isn't set in the ambient shell/CI environment.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from core.config import Config, ProviderConfig, SecretValue
from core.startup_validation import (
    StartupValidationError,
    validate_startup_environment,
)
from providers.base_provider import BaseProvider, ProviderConfig as PC
from providers.registry import ProviderRegistry


class _DummyProvider(BaseProvider):
    """Minimal concrete BaseProvider so ProviderRegistry has something to hold."""

    def initialize(self, config: PC) -> None:
        pass

    def generate(self, prompt: str, **kwargs):
        raise NotImplementedError

    def health_check(self) -> bool:
        return True

    def close(self) -> None:
        pass


def _make_config(**provider_overrides) -> Config:
    """Build a Config with sane defaults, overriding only ProviderConfig fields."""
    base = ProviderConfig(
        openai_api_key=SecretValue("sk-test-key"),
        active_provider="openai",
        model="gpt-4o",
        timeout_seconds=30.0,
        temperature=0.7,
    )
    providers = replace(base, **provider_overrides)
    return Config(providers=providers)


class TestValidConfigPasses(unittest.TestCase):
    def test_valid_config_returns_same_config(self):
        config = _make_config()
        result = validate_startup_environment(config=config)
        self.assertIs(result, config)


class TestProviderNameValidity(unittest.TestCase):
    def test_empty_provider_name_raises(self):
        config = _make_config(active_provider="")
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_unknown_provider_name_raises(self):
        config = _make_config(active_provider="not-a-real-provider")
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_all_known_providers_pass_structural_check(self):
        # ollama needs no key; the rest get a matching key via overrides.
        for name in ("openai", "gemini", "claude", "grok", "deepseek", "openrouter"):
            key_field = f"{name}_api_key"
            config = _make_config(
                active_provider=name,
                **{key_field: SecretValue("test-key")},
            )
            validate_startup_environment(config=config)  # should not raise

        config = _make_config(active_provider="ollama")
        validate_startup_environment(config=config)  # should not raise

    def test_registry_cross_check_rejects_unregistered_provider(self):
        config = _make_config(active_provider="claude", claude_api_key=SecretValue("k"))
        empty_registry = ProviderRegistry()
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config, registry=empty_registry)

    def test_registry_cross_check_accepts_registered_provider(self):
        config = _make_config(active_provider="claude", claude_api_key=SecretValue("k"))
        registry = ProviderRegistry()
        registry.register("claude", _DummyProvider())
        validate_startup_environment(config=config, registry=registry)  # should not raise


class TestModelNameValidity(unittest.TestCase):
    def test_empty_model_name_raises(self):
        config = _make_config(model="")
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_whitespace_only_model_name_raises(self):
        config = _make_config(model="   ")
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)


class TestTimeoutValidity(unittest.TestCase):
    def test_zero_timeout_raises(self):
        config = _make_config(timeout_seconds=0.0)
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_negative_timeout_raises(self):
        config = _make_config(timeout_seconds=-5.0)
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_infinite_timeout_raises(self):
        config = _make_config(timeout_seconds=float("inf"))
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)


class TestTemperatureValidity(unittest.TestCase):
    def test_negative_temperature_raises(self):
        config = _make_config(temperature=-0.1)
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_temperature_above_max_raises(self):
        config = _make_config(temperature=2.1)
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_boundary_temperatures_pass(self):
        for temp in (0.0, 2.0):
            config = _make_config(temperature=temp)
            validate_startup_environment(config=config)  # should not raise


class TestRequiredApiKey(unittest.TestCase):
    def test_missing_key_for_selected_provider_raises(self):
        config = _make_config(active_provider="gemini", gemini_api_key=None)
        with self.assertRaises(StartupValidationError):
            validate_startup_environment(config=config)

    def test_key_for_non_selected_provider_is_never_checked(self):
        # openai is selected and has a key; gemini has none. Must still pass.
        config = _make_config(active_provider="openai", gemini_api_key=None)
        validate_startup_environment(config=config)  # should not raise

    def test_ollama_requires_no_api_key(self):
        config = _make_config(active_provider="ollama", openai_api_key=None)
        validate_startup_environment(config=config)  # should not raise

    def test_error_message_never_contains_secret_value(self):
        config = _make_config(active_provider="gemini", gemini_api_key=None)
        try:
            validate_startup_environment(config=config)
            self.fail("expected StartupValidationError")
        except StartupValidationError as exc:
            self.assertNotIn("sk-test-key", str(exc))


if __name__ == "__main__":
    unittest.main()
