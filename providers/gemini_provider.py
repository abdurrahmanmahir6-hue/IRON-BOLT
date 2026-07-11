"""
providers/gemini_provider.py

Concrete BaseProvider implementation backed by the Google Gemini SDK.
Supports both the legacy `google-generativeai` and the new `google-genai` SDKs.
"""

from __future__ import annotations

import logging
import warnings
import sys
from typing import Any, ClassVar, Optional

# Suppress the deprecation warning for the old SDK if it appears during import
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
try:
    # Pre-emptively disable the warning by setting the flag in the module before it's fully loaded if possible,
    # or just use the filter. Since it's a module-level warning on import, we try this:
    import google.generativeai as genai
    _HAS_LEGACY_SDK = True
except ImportError:
    _HAS_LEGACY_SDK = False

try:
    from google import genai as new_genai
    _HAS_NEW_SDK = True
except ImportError:
    _HAS_NEW_SDK = False

from providers.base_provider import BaseProvider, ProviderConfig, ProviderResponse
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderRequestError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini models.

    Supports graceful fallback between the new google-genai and legacy 
    google-generativeai SDKs.
    """

    PROVIDER_NAME: ClassVar[str] = "gemini"

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._model: Optional[str] = None
        self._initialized: bool = False
        self._use_new_sdk: bool = False

    def initialize(self, config: ProviderConfig) -> None:
        """
        Initialize the Gemini client.
        """
        if not config.api_key:
            raise ProviderConfigurationError("GeminiProvider requires an API key.")
        if not config.model:
            raise ProviderConfigurationError("GeminiProvider requires a model name.")

        try:
            if _HAS_NEW_SDK:
                self._client = new_genai.Client(api_key=config.api_key)
                self._use_new_sdk = True
            elif _HAS_LEGACY_SDK:
                genai.configure(api_key=config.api_key)
                self._client = genai.GenerativeModel(config.model)
                self._use_new_sdk = False
            else:
                raise ProviderInitializationError(
                    "No Gemini SDK installed. Install google-genai or google-generativeai."
                )
        except Exception as e:
            raise ProviderInitializationError(f"Failed to initialize Gemini client: {e}")

        self._model = config.model
        self._initialized = True
        logger.info("GeminiProvider initialized (model=%s, new_sdk=%s)", self._model, self._use_new_sdk)

    def generate(self, prompt: str, **kwargs: Any) -> ProviderResponse:
        """
        Generate a response using the Gemini API.
        """
        if not self._initialized:
            raise ProviderInitializationError("GeminiProvider not initialized.")

        try:
            if self._use_new_sdk:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=kwargs
                )
                content = response.text
            else:
                response = self._client.generate_content(prompt, **kwargs)
                content = response.text
            
            return ProviderResponse(
                content=content,
                provider_name=self.PROVIDER_NAME,
                raw=response
            )
        except Exception as e:
            raise ProviderRequestError(f"Gemini generation failed: {e}")

    def health_check(self) -> bool:
        """
        Perform a simple health check.
        """
        if not self._initialized:
            return False
        try:
            # Simple probe: list models or just return True if initialized
            # For Gemini, listing models is a good health check
            if self._use_new_sdk:
                self._client.models.list()
            else:
                genai.list_models()
            return True
        except Exception as e:
            logger.warning("Gemini health check failed: %s", e)
            return False

    def close(self) -> None:
        """
        Clean up resources.
        """
        self._client = None
        self._initialized = False
