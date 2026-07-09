"""
tests/test_openai_provider.py

Sprint 3 Task 5 test suite for providers/openai_provider.py.

Every test in this file mocks `providers.openai_provider.OpenAI` (the SDK
client class) directly — no test in this file makes, or can make, a real
network call to OpenAI's API. This module also requires no environment
variables and does not touch core.config, matching the architectural
boundary documented in openai_provider.py (providers/ imports nothing
from core/config).

Stdlib-only: `unittest` + `unittest.mock`, no pytest dependency, matching
the existing Sprint 2/3 test suite convention.

# AI-generated
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from providers.base_provider import ProviderConfig, ProviderResponse
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderRequestError,
)
from providers.openai_provider import OpenAIProvider, OpenAISDKError
from providers.provider_manager import ProviderManager
from providers.registry import ProviderRegistry


def _valid_config(**overrides) -> ProviderConfig:
    """Build a minimal, valid ProviderConfig for OpenAIProvider tests."""
    base = {
        "api_key": "sk-test-key-not-real",
        "model": "gpt-4o-mini",
        "extra": {},
    }
    base.update(overrides)
    return ProviderConfig(**base)


class TestOpenAIProviderRegistration(unittest.TestCase):
    """Category 1: OpenAIProvider registration."""

    def test_can_be_registered_under_openai_name(self) -> None:
        registry = ProviderRegistry()
        provider = OpenAIProvider()

        registry.register("openai", provider)

        self.assertTrue(registry.is_registered("openai"))
        self.assertIs(registry.get("openai"), provider)

    def test_registering_same_name_twice_raises(self) -> None:
        registry = ProviderRegistry()
        registry.register("openai", OpenAIProvider())

        with self.assertRaises(ValueError):
            registry.register("openai", OpenAIProvider())


class TestProviderManagerResolvesOpenAIProvider(unittest.TestCase):
    """Category 4: ProviderManager correctly resolving OpenAIProvider."""

    def test_get_provider_returns_the_registered_openai_instance(self) -> None:
        registry = ProviderRegistry()
        provider = OpenAIProvider()
        registry.register("openai", provider)
        manager = ProviderManager(registry)

        resolved = manager.get_provider("openai")

        self.assertIs(resolved, provider)
        self.assertIsInstance(resolved, OpenAIProvider)

    def test_get_provider_unknown_name_raises_key_error(self) -> None:
        manager = ProviderManager(ProviderRegistry())

        with self.assertRaises(KeyError):
            manager.get_provider("openai")


class TestOpenAIProviderInitialize(unittest.TestCase):
    """Category 2 & 5: successful initialization and client creation
    (mocked — never a real API call)."""

    @patch("providers.openai_provider.OpenAI")
    def test_initialize_success_creates_client_with_config_values(
        self, mock_openai_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        config = _valid_config(
            extra={"timeout_seconds": 15.0, "base_url": "https://example.test/v1"}
        )

        provider.initialize(config)

        mock_openai_cls.assert_called_once_with(
            api_key="sk-test-key-not-real",
            base_url="https://example.test/v1",
            timeout=15.0,
        )
        self.assertTrue(provider._initialized)
        self.assertIs(provider._client, mock_client)
        self.assertEqual(provider._model, "gpt-4o-mini")

    @patch("providers.openai_provider.OpenAI")
    def test_initialize_without_extra_uses_sdk_defaults(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider = OpenAIProvider()
        config = _valid_config()  # extra={}

        provider.initialize(config)

        mock_openai_cls.assert_called_once_with(
            api_key="sk-test-key-not-real",
            base_url=None,
            timeout=None,
        )

    @patch("providers.openai_provider.OpenAI")
    def test_initialize_missing_api_key_raises_configuration_error(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider = OpenAIProvider()
        config = _valid_config(api_key=None)

        with self.assertRaises(ProviderConfigurationError):
            provider.initialize(config)

        mock_openai_cls.assert_not_called()

    @patch("providers.openai_provider.OpenAI")
    def test_initialize_missing_model_raises_configuration_error(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider = OpenAIProvider()
        config = _valid_config(model=None)

        with self.assertRaises(ProviderConfigurationError):
            provider.initialize(config)

        mock_openai_cls.assert_not_called()

    @patch("providers.openai_provider.OpenAI")
    def test_initialize_client_construction_failure_wrapped(
        self, mock_openai_cls: MagicMock
    ) -> None:
        mock_openai_cls.side_effect = OpenAISDKError("boom")
        provider = OpenAIProvider()

        with self.assertRaises(ProviderInitializationError):
            provider.initialize(_valid_config())


class TestOpenAIProviderGenerate(unittest.TestCase):
    """generate() behavior — success, pre-init guard, SDK error wrapping."""

    def _initialized_provider(self, mock_openai_cls: MagicMock) -> tuple:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        provider.initialize(_valid_config())
        return provider, mock_client

    @patch("providers.openai_provider.OpenAI")
    def test_generate_returns_provider_response(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider, mock_client = self._initialized_provider(mock_openai_cls)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="hello!"))]
        mock_client.chat.completions.create.return_value = mock_completion

        response = provider.generate("hi there")

        self.assertIsInstance(response, ProviderResponse)
        self.assertEqual(response.content, "hello!")
        self.assertEqual(response.provider_name, "openai")
        self.assertIs(response.raw, mock_completion)
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi there"}],
        )

    @patch("providers.openai_provider.OpenAI")
    def test_generate_forwards_extra_kwargs(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider, mock_client = self._initialized_provider(mock_openai_cls)
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_client.chat.completions.create.return_value = mock_completion

        provider.generate("hi", temperature=0.2, max_tokens=50)

        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.2,
            max_tokens=50,
        )

    def test_generate_before_initialize_raises(self) -> None:
        provider = OpenAIProvider()

        with self.assertRaises(ProviderInitializationError):
            provider.generate("hi")

    @patch("providers.openai_provider.OpenAI")
    def test_generate_sdk_error_wrapped_as_provider_request_error(
        self, mock_openai_cls: MagicMock
    ) -> None:
        provider, mock_client = self._initialized_provider(mock_openai_cls)
        mock_client.chat.completions.create.side_effect = OpenAISDKError("rate limited")

        with self.assertRaises(ProviderRequestError):
            provider.generate("hi")


class TestOpenAIProviderHealthCheck(unittest.TestCase):
    """health_check() never raises — always returns a plain bool."""

    def test_health_check_before_initialize_returns_false(self) -> None:
        provider = OpenAIProvider()
        self.assertFalse(provider.health_check())

    @patch("providers.openai_provider.OpenAI")
    def test_health_check_success_returns_true(
        self, mock_openai_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        provider.initialize(_valid_config())

        self.assertTrue(provider.health_check())
        mock_client.models.list.assert_called_once()

    @patch("providers.openai_provider.OpenAI")
    def test_health_check_sdk_error_returns_false_not_raise(
        self, mock_openai_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.models.list.side_effect = OpenAISDKError("down")
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        provider.initialize(_valid_config())

        self.assertFalse(provider.health_check())


class TestOpenAIProviderClose(unittest.TestCase):
    """close() releases resources and is safe to call repeatedly."""

    def test_close_before_initialize_is_a_safe_no_op(self) -> None:
        provider = OpenAIProvider()
        provider.close()  # must not raise

    @patch("providers.openai_provider.OpenAI")
    def test_close_releases_client_and_resets_state(
        self, mock_openai_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        provider.initialize(_valid_config())

        provider.close()

        mock_client.close.assert_called_once()
        self.assertIsNone(provider._client)
        self.assertFalse(provider._initialized)

    @patch("providers.openai_provider.OpenAI")
    def test_close_is_idempotent(self, mock_openai_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = OpenAIProvider()
        provider.initialize(_valid_config())

        provider.close()
        provider.close()  # second call must not raise

        mock_client.close.assert_called_once()  # only invoked once


if __name__ == "__main__":
    unittest.main()
