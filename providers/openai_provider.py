"""
providers/openai_provider.py

Compatibility module and OpenAIProvider implementation.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, ClassVar, Optional, Union

from openai import OpenAI, OpenAIError as OpenAISDKError

from providers.base_provider import BaseProvider
from providers.models.provider_config import ProviderConfig
from providers.models.provider_request import ProviderRequest
from providers.models.provider_response import ProviderResponse
from providers.models.provider_capability import ProviderCapability
from providers.models.provider_info import ProviderInfo
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderRequestError,
)
from providers.openai.capability import OPENAI_CAPABILITIES
from providers.openai.constants import (
    PROVIDER_NAME,
    DISPLAY_NAME,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_BASE_URL,
)
from providers.openai.mapper import OpenAIMapper

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider adapter supporting both prompt strings and ProviderRequest.
    """

    PROVIDER_NAME: ClassVar[str] = PROVIDER_NAME
    DISPLAY_NAME: ClassVar[str] = DISPLAY_NAME

    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None
        self._model: Optional[str] = None
        self._initialized: bool = False
        self._mapper: OpenAIMapper = OpenAIMapper()

    def initialize(self, config: ProviderConfig) -> None:
        """Initialize the OpenAI provider from config."""
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

        extra = config.extra or {}
        timeout = extra.get("timeout_seconds")
        base_url = extra.get("base_url")

        try:
            self._client = OpenAI(
                api_key=config.api_key,
                base_url=base_url,
                timeout=timeout,
            )
        except OpenAISDKError as exc:
            raise ProviderInitializationError(str(exc)) from exc

        self._model = config.model
        self._initialized = True
        logger.info(
            "%s initialized | provider=%s | model=%s",
            self.__class__.__name__,
            PROVIDER_NAME,
            self._model,
        )

    def generate(
        self,
        prompt: Union[str, ProviderRequest],
        **kwargs: Any,
    ) -> ProviderResponse:
        """Generate a response using either a prompt string or ProviderRequest."""
        if not self._initialized or self._client is None or not self._model:
            raise ProviderInitializationError(
                f"{self.__class__.__name__} is not initialized. Call initialize(config) first."
            )

        if isinstance(prompt, str):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs,
                )
                content = (
                    completion.choices[0].message.content
                    if completion.choices
                    else ""
                )
                return ProviderResponse(
                    content=content,
                    provider_name=PROVIDER_NAME,
                    raw=completion,
                )
            except OpenAISDKError as exc:
                raise ProviderRequestError(str(exc)) from exc

        # Handle ProviderRequest
        request_payload = self._mapper.to_sdk_request(prompt)
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                **request_payload,
                **kwargs,
            )
            return self._mapper.to_provider_response(completion, 0.0, "req-id")
        except OpenAISDKError as exc:
            raise ProviderRequestError(str(exc)) from exc

    def health_check(self) -> bool:
        """Verify reachability using models.list(). Never raises."""
        if not self._initialized or self._client is None:
            return False
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Release held client resources."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._model = None
        self._initialized = False

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=PROVIDER_NAME,
            display_name=DISPLAY_NAME,
            provider=self,
            capabilities=ProviderCapability(supported=set(OPENAI_CAPABILITIES)),
        )

    def get_capabilities(self) -> list[ProviderCapability]:
        return list(OPENAI_CAPABILITIES)


# Ensure that patching providers.openai_provider.OpenAI propagates if needed
class _OpenAIProviderModule(sys.modules[__name__].__class__):
    pass

sys.modules[__name__].__class__ = _OpenAIProviderModule

__all__ = ["OpenAIProvider", "OpenAI", "OpenAISDKError"]
