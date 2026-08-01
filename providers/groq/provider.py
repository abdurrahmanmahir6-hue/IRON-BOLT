"""
providers/groq/provider.py

Concrete BaseProvider implementation backed by the Groq SDK.

IRON-BOLT Provider Layer — Groq package (aligned with OpenAI / Gemini
architecture after Capability, Constants, Mapper, and Translator phases).

Design summary
---------------
GroqProvider is a thin lifecycle / SDK adapter. After the redesign it is
responsible only for:

- validating configuration
- creating and owning the Groq SDK client
- calling GroqMapper for request / response conversion
- invoking the Groq SDK
- delegating SDK exception translation to GroqExceptionTranslator
- returning a framework ProviderResponse

It must NOT:

- build SDK request payloads
- parse SDK responses
- contain capability definitions
- contain provider constants
- contain SDK-exception mapping logic

IB-AR alignment:
    - Chapter 7  (Tool Rules): thin orchestration only.
    - Chapter 9  (Coding Standard): full type hints, snake_case, docs.
    - Dependency Inversion: depends on BaseExceptionTranslator and
      GroqMapper abstractions; Core never sees Groq SDK types.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Optional

from groq import Groq

from providers.base_provider import BaseProvider, ProviderConfig, ProviderResponse
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderError,
)
from providers.groq.capability import GROQ_CAPABILITIES
from providers.groq.constants import PROVIDER_NAME
from providers.groq.mapper import GroqMapper
from providers.translators.base import BaseExceptionTranslator
from providers.translators.groq import GroqExceptionTranslator
from providers.models import ProviderCapability

logger = logging.getLogger(__name__)


class GroqProvider(BaseProvider):
    """
    Provider implementation for Groq-hosted models.

    The Groq Python SDK mirrors the OpenAI chat-completions surface
    (``client.chat.completions.create``). All request construction and
    response parsing are delegated to ``GroqMapper``; all SDK exception
    translation is delegated to ``GroqExceptionTranslator``.
    """

    PROVIDER_NAME: ClassVar[str] = PROVIDER_NAME

    def __init__(self) -> None:
        self._client: Optional[Groq] = None
        self._model: Optional[str] = None
        self._initialized: bool = False
        self._mapper: GroqMapper = GroqMapper()
        self._translator: BaseExceptionTranslator = GroqExceptionTranslator()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def initialize(self, config: ProviderConfig) -> None:
        """
        Validate configuration and create the Groq SDK client.

        Raises
        ------
        ProviderConfigurationError
            When required fields (api_key, model) are missing.
        ProviderInitializationError
            When the SDK client cannot be constructed.
        """
        if not config.api_key:
            raise ProviderConfigurationError("GroqProvider requires an API key.")
        if not config.model:
            raise ProviderConfigurationError("GroqProvider requires a model name.")

        try:
            client_kwargs: dict[str, Any] = {"api_key": config.api_key}

            extra = config.extra or {}
            timeout = extra.get("timeout_seconds", extra.get("timeout"))
            if timeout is not None:
                client_kwargs["timeout"] = timeout

            base_url = extra.get("base_url")
            if base_url is not None:
                client_kwargs["base_url"] = base_url

            self._client = Groq(**client_kwargs)
        except Exception as exc:
            raise self._translator.translate(exc) from exc

        self._model = config.model
        self._initialized = True
        logger.info(
            "%s initialized (model=%s)",
            PROVIDER_NAME,
            self._model,
        )

    def close(self) -> None:
        """
        Release the SDK client and mark the provider as uninitialized.

        Soft-fail: teardown must not raise into the caller.
        """
        self._client = None
        self._model = None
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str, **kwargs: Any) -> ProviderResponse:
        """
        Generate a completion for *prompt* via the Groq chat API.

        Parameters
        ----------
        prompt:
            User text to send as a single user message.
        **kwargs:
            Extra generation parameters forwarded to the SDK
            (temperature, max_completion_tokens, stream, tools, …).

        Returns
        -------
        ProviderResponse
            Framework-normalized response produced by ``GroqMapper``.

        Raises
        ------
        ProviderInitializationError
            When ``initialize()`` has not been called successfully.
        Provider*Error
            Any SDK failure translated by ``GroqExceptionTranslator``.
        """
        if not self._initialized or self._client is None or self._model is None:
            raise ProviderInitializationError("GroqProvider not initialized.")

        try:
            sdk_request = self._mapper.to_sdk_request(
                prompt=prompt,
                model=self._model,
                kwargs=kwargs,
            )
            completion = self._client.chat.completions.create(**sdk_request)
            return self._mapper.to_provider_response(completion)
        except ProviderError:
            raise
        except Exception as exc:
            raise self._translator.translate(exc) from exc

    # ------------------------------------------------------------------ #
    # Health / capabilities
    # ------------------------------------------------------------------ #

    def health_check(self) -> bool:
        """
        Soft health probe.

        Returns True when the provider is initialized and a lightweight
        models-list call succeeds; False otherwise. Never raises.
        """
        if not self._initialized or self._client is None:
            return False
        try:
            self._client.models.list()
            return True
        except Exception as exc:
            logger.warning("%s health check failed: %s", PROVIDER_NAME, exc)
            return False

    def get_capabilities(self) -> list[ProviderCapability]:
        """
        Return the static capability list declared in capability.py.
        """
        return list(GROQ_CAPABILITIES)
