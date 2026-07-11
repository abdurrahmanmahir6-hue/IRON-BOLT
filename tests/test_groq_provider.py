"""
tests/test_groq_provider.py

Unit tests for providers/groq_provider.py.

Testing philosophy (matches test_openai_provider.py / test_gemini_provider.py):
    - stdlib `unittest` only; no pytest dependency required.
    - The `groq` SDK's `Groq` class is patched at the module level
      (`providers.groq_provider.Groq`) so no real network call or real
      API key is ever needed.
    - Each test covers exactly one behavior: registration, initialization,
      generate(), health_check(), close(), ProviderManager resolution,
      configuration validation, request failures, and initialization
      failures.

# AI-generated
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from groq import GroqError as GroqSDKError

from providers.base_provider import ProviderConfig, ProviderResponse
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderRequestError,
)
from providers.groq_provider import GroqProvider
from providers.provider_manager import ProviderManager
from providers.registry import ProviderRegistry


def _make_config(**overrides: object) -> ProviderConfig:
    """Build a valid ProviderConfig for GroqProvider, with overrides."""
    defaults = {
        "api_key": "gsk_test_key",
        "model": "openai/gpt-oss-120b",
        "extra": {},
    }
    defaults.update(overrides)
    return ProviderConfig(**defaults)  # type: ignore[arg-type]


def _make_completion(text: str = "Hello from Groq") -> MagicMock:
    """Build a fake SDK completion object shaped like the real response."""
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = text
    return completion


class TestGroqProviderInitialize(unittest.TestCase):
    """initialize() — configuration validation and client construction."""

    @patch("providers.groq_provider.Groq")
    def test_initialize_success_builds_client_with_expected_args(
        self, mock_groq_cls: MagicMock
    ) -> None:
        provider = GroqProvider()
        config = _make_config(
            extra={"timeout_seconds": 15.0, "base_url": "https://api.groq.com"}
        )

        provider.initialize(config)

        mock_groq_cls.assert_called_once_with(
            api_key="gsk_test_key",
            base_url="https://api.groq.com",
            timeout=15.0,
        )
        self.assertTrue(provider._initialized)
        self.assertEqual(provider._model, "openai/gpt-oss-120b")

    @patch("providers.groq_provider.Groq")
    def test_initialize_without_optional_extra_uses_sdk_defaults(
        self, mock_groq_cls: MagicMock
    ) -> None:
        provider = GroqProvider()
        provider.initialize(_make_config())

        mock_groq_cls.assert_called_once_with(
            api_key="gsk_test_key", base_url=None, timeout=None
        )

    def test_initialize_missing_api_key_raises_configuration_error(self) -> None:
        provider = GroqProvider()
        config = _make_config(api_key=None)

        with self.assertRaises(ProviderConfigurationError):
            provider.initialize(config)
        self.assertFalse(provider._initialized)

    def test_initialize_missing_model_raises_configuration_error(self) -> None:
        provider = GroqProvider()
        config = _make_config(model=None)

        with self.assertRaises(ProviderConfigurationError):
            provider.initialize(config)
        self.assertFalse(provider._initialized)

    @patch("providers.groq_provider.Groq")
    def test_initialize_sdk_failure_raises_initialization_error(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_groq_cls.side_effect = GroqSDKError("bad base_url")
        provider = GroqProvider()

        with self.assertRaises(ProviderInitializationError):
            provider.initialize(_make_config())
        self.assertFalse(provider._initialized)


class TestGroqProviderGenerate(unittest.TestCase):
    """generate() — happy path, pre-init guard, and SDK failure mapping."""

    @patch("providers.groq_provider.Groq")
    def test_generate_returns_provider_response(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion(
            "hi there"
        )
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())
        response = provider.generate("Say hi")

        self.assertIsInstance(response, ProviderResponse)
        self.assertEqual(response.content, "hi there")
        self.assertEqual(response.provider_name, "groq")
        mock_client.chat.completions.create.assert_called_once_with(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "Say hi"}],
        )

    @patch("providers.groq_provider.Groq")
    def test_generate_forwards_kwargs_to_sdk(self, mock_groq_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion()
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())
        provider.generate("Say hi", temperature=0.2, max_completion_tokens=256)

        mock_client.chat.completions.create.assert_called_once_with(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "Say hi"}],
            temperature=0.2,
            max_completion_tokens=256,
        )

    @patch("providers.groq_provider.Groq")
    def test_generate_handles_missing_content_gracefully(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion(None)
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())
        response = provider.generate("Say hi")

        self.assertEqual(response.content, "")

    def test_generate_before_initialize_raises_initialization_error(self) -> None:
        provider = GroqProvider()
        with self.assertRaises(ProviderInitializationError):
            provider.generate("Say hi")

    @patch("providers.groq_provider.Groq")
    def test_generate_sdk_failure_raises_request_error(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = GroqSDKError(
            "rate limited"
        )
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())

        with self.assertRaises(ProviderRequestError):
            provider.generate("Say hi")


class TestGroqProviderHealthCheck(unittest.TestCase):
    """health_check() — never raises, reflects live client state."""

    def test_health_check_before_initialize_returns_false(self) -> None:
        provider = GroqProvider()
        self.assertFalse(provider.health_check())

    @patch("providers.groq_provider.Groq")
    def test_health_check_success_returns_true(self, mock_groq_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())

        self.assertTrue(provider.health_check())
        mock_client.models.list.assert_called_once_with()

    @patch("providers.groq_provider.Groq")
    def test_health_check_sdk_failure_returns_false(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.models.list.side_effect = GroqSDKError("unreachable")
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())

        self.assertFalse(provider.health_check())


class TestGroqProviderClose(unittest.TestCase):
    """close() — idempotent, safe pre-init, resets internal state."""

    def test_close_before_initialize_is_a_safe_noop(self) -> None:
        provider = GroqProvider()
        provider.close()  # must not raise
        self.assertFalse(provider._initialized)

    @patch("providers.groq_provider.Groq")
    def test_close_releases_client_and_resets_state(
        self, mock_groq_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())
        provider.close()

        mock_client.close.assert_called_once_with()
        self.assertIsNone(provider._client)
        self.assertFalse(provider._initialized)

    @patch("providers.groq_provider.Groq")
    def test_close_is_idempotent(self, mock_groq_cls: MagicMock) -> None:
        mock_groq_cls.return_value = MagicMock()
        provider = GroqProvider()
        provider.initialize(_make_config())

        provider.close()
        provider.close()  # second call must not raise

        self.assertFalse(provider._initialized)

    @patch("providers.groq_provider.Groq")
    def test_close_swallows_sdk_close_errors(self, mock_groq_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.close.side_effect = RuntimeError("socket already gone")
        mock_groq_cls.return_value = mock_client

        provider = GroqProvider()
        provider.initialize(_make_config())
        provider.close()  # must not raise despite close() failing internally

        self.assertIsNone(provider._client)
        self.assertFalse(provider._initialized)


class TestGroqProviderRegistryAndManager(unittest.TestCase):
    """Registration and resolution through ProviderRegistry / ProviderManager."""

    def test_registers_under_groq_name(self) -> None:
        registry = ProviderRegistry()
        provider = GroqProvider()

        registry.register("groq", provider)

        self.assertTrue(registry.is_registered("groq"))
        self.assertIs(registry.get("groq"), provider)

    def test_duplicate_registration_raises_value_error(self) -> None:
        registry = ProviderRegistry()
        registry.register("groq", GroqProvider())

        with self.assertRaises(ValueError):
            registry.register("groq", GroqProvider())

    def test_openai_and_gemini_slots_remain_free_after_groq_registration(
        self,
    ) -> None:
        """Registering Groq must not interfere with other provider names."""
        registry = ProviderRegistry()
        registry.register("groq", GroqProvider())

        self.assertFalse(registry.is_registered("openai"))
        self.assertFalse(registry.is_registered("gemini"))

    def test_provider_manager_resolves_groq_by_name(self) -> None:
        registry = ProviderRegistry()
        provider = GroqProvider()
        registry.register("groq", provider)
        manager = ProviderManager(registry)

        resolved = manager.get_provider("groq")

        self.assertIs(resolved, provider)

    @patch("providers.groq_provider.Groq")
    def test_manager_resolved_provider_is_fully_usable(
        self, mock_groq_cls: MagicMock
    ) -> None:
        """End-to-end: register -> resolve via manager -> initialize -> generate."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("ok")
        mock_groq_cls.return_value = mock_client

        registry = ProviderRegistry()
        registry.register("groq", GroqProvider())
        manager = ProviderManager(registry)

        provider = manager.get_provider("groq")
        provider.initialize(_make_config())
        response = provider.generate("ping")

        self.assertEqual(response.content, "ok")
        self.assertEqual(response.provider_name, "groq")


if __name__ == "__main__":
    unittest.main()
