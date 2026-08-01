"""
providers/openai/provider.py

Concrete BaseProvider implementation acting as a pure adapter for the
official OpenAI Python SDK. Sprint 3 Task 5 (AR1 Redesign) — Phase 3
(Provider Metadata & Capability Extraction).

Design summary (AR1 Redesign, Phase 3)
----------------------------------------
OpenAIProvider implements the lifecycle declared by BaseProvider and acts
strictly as an SDK adapter. It no longer owns static metadata or
capability definitions; those live in constants.py and capability.py.

- Input: ProviderRequest (containing messages, system_prompt, tools, etc.)
- Output: ProviderResponse (containing usage, latency, finish_reason, etc.)
- Capabilities: Exposed via get_capabilities() which returns the
  centralized OPENAI_CAPABILITIES tuple.
- Conversion: All ProviderRequest -> SDK request and SDK response ->
  ProviderResponse mapping is delegated to OpenAIMapper (mapper.py). The
  provider itself only validates config, owns the SDK client, drives the
  request lifecycle (timing, request-id generation, logging), and calls
  the SDK.
- Exceptions: SDK exceptions (openai.OpenAIError) are allowed to bubble up
  to the Translator layer, keeping the Core SDK-agnostic.

IB-AR alignment:
    - Chapter 2  (Transparency / Fail-Fast): initialize() validates
      config eagerly.
    - Chapter 7  (Tool Rules): strictly follows the ProviderRequest/
      ProviderResponse contracts; capabilities are externalized.
    - Chapter 9  (Coding Standard): AI-generated, snake_case,
      PascalCase, full type hints.
    - Chapter 10 (Security): API key is never logged or exposed.
"""

from __future__ import annotations

import logging
import time
import uuid

from openai import OpenAI

from providers.base_provider import BaseProvider
from providers.models.provider_config import ProviderConfig
from providers.models.provider_request import ProviderRequest
from providers.models.provider_response import ProviderResponse
from providers.models.provider_capability import ProviderCapability
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
)
from providers.openai.mapper import OpenAIMapper
from providers.openai.capability import OPENAI_CAPABILITIES
from providers.openai.constants import (
    PROVIDER_NAME,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_BASE_URL,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    BaseProvider adapter for the official `openai` SDK.

    This class is strictly a thin adapter. It owns the SDK client and
    drives the request lifecycle (timing, request-id generation,
    logging), delegating all ProviderRequest/ProviderResponse
    conversion to OpenAIMapper. Static metadata and capabilities live
    in constants.py and capability.py. Exception translation is handled
    by the external Translator layer.
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self._model: str | None = None
        self._initialized: bool = False
        self._mapper: OpenAIMapper = OpenAIMapper()

    # ------------------------------------------------------------------ #
    # Lifecycle: initialize
    # ------------------------------------------------------------------ #

    def initialize(self, config: ProviderConfig) -> None:
        """
        Build the reusable OpenAI SDK client from the given ProviderConfig.
        """
        self._validate_config(config)
        self._client = self._create_client(config)
        self._store_runtime_state(config)

        logger.info(
            "%s initialized | provider=%s | model=%s",
            self.__class__.__name__,
            PROVIDER_NAME,
            self._model,
        )

    def _validate_config(self, config: ProviderConfig) -> None:
        """Validate required configuration parameters."""
        if not config.api_key:
            raise ProviderConfigurationError(
                f"{self.__class__.__name__}.initialize() requires "
                "ProviderConfig.api_key to be set."
            )
        if not config.model:
            raise ProviderConfigurationError(
                f"{self.__class__.__name__}.initialize() requires "
                "ProviderConfig.model to be set."
            )

    def _create_client(self, config: ProviderConfig) -> OpenAI:
        """Instantiate the OpenAI SDK client."""
        timeout = config.extra.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        base_url = config.extra.get("base_url", DEFAULT_BASE_URL)

        # SDK exceptions will bubble up to the Translator layer
        return OpenAI(
            api_key=config.api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def _store_runtime_state(self, config: ProviderConfig) -> None:
        """Store validated runtime state."""
        self._model = config.model
        self._initialized = True

    # ------------------------------------------------------------------ #
    # Lifecycle: generate
    # ------------------------------------------------------------------ #

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        Generate a completion via the OpenAI Chat Completions API.
        """
        self._require_client()
        self._require_model()

        request_payload = self._mapper.to_sdk_request(request)

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # SDK exceptions bubble up to the Translator layer
        completion = self._client.chat.completions.create(
            model=self._model,
            **request_payload,
        )

        latency = time.perf_counter() - start_time

        logger.info(
            "%s generate completed | provider=%s | model=%s | latency=%.4f | request_id=%s",
            self.__class__.__name__,
            PROVIDER_NAME,
            self._model,
            latency,
            request_id,
        )

        return self._mapper.to_provider_response(completion, latency, request_id)

    # ------------------------------------------------------------------ #
    # Capabilities
    # ------------------------------------------------------------------ #

    def get_capabilities(self) -> list[ProviderCapability]:
        """
        Return the list of capabilities supported by this provider.
        Registry uses this to route requests intelligently.

        The concrete set is defined once in capability.OPENAI_CAPABILITIES.
        """
        return list(OPENAI_CAPABILITIES)

    # ------------------------------------------------------------------ #
    # Lifecycle: health_check
    # ------------------------------------------------------------------ #

    def health_check(self) -> bool:
        """
        Verify the provider is reachable.
        Uses `models.list()` to avoid consuming generation tokens.
        """
        if not self._initialized or self._client is None:
            return False
        try:
            self._client.models.list()
            return True
        except Exception as exc:
            logger.warning(
                "%s.health_check() failed: %s",
                self.__class__.__name__,
                exc,
            )
            return False

    # ------------------------------------------------------------------ #
    # Lifecycle: close
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """
        Release resources and reset runtime state consistently.
        """
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.warning(
                    "%s.close() raised: %s",
                    self.__class__.__name__,
                    exc,
                )

        self._client = None
        self._model = None
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_client(self) -> None:
        """Guard to ensure the SDK client is initialized."""
        if self._client is None:
            raise ProviderInitializationError(
                f"{self.__class__.__name__} client is not initialized. "
                "Call initialize(config) first."
            )

    def _require_model(self) -> None:
        """Guard to ensure the model is set."""
        if not self._model:
            raise ProviderInitializationError(
                f"{self.__class__.__name__} model is not set. "
                "Call initialize(config) first."
            )