"""
providers/openai_provider.py

Concrete BaseProvider implementation backed by the official OpenAI Python
SDK. Sprint 3 Task 5.

Design summary
---------------
OpenAIProvider implements exactly the four-method lifecycle declared by
BaseProvider (initialize / generate / health_check / close) and nothing
more. All OpenAI-specific detail — the SDK import, the client construction,
the chat.completions.create() call shape, the models.list() health probe —
is private to this file. ProviderManager and the Registry never see any of
it; they only ever hold a BaseProvider reference.

Where configuration comes from
-------------------------------
This file does NOT import core.config or call get_config(). That is a
deliberate boundary, not an oversight: core/config.py's own docstring
states that "providers/ already imports nothing from core/config" (to
avoid a circular import with core/startup_validation.py, which is the one
module allowed to depend on both). OpenAIProvider therefore only ever
reads the providers.base_provider.ProviderConfig it is handed via
initialize() — api_key, model, and an `extra` dict for anything that
doesn't fit the common shape (here: timeout_seconds, base_url).

Translating the application-wide core.config.Config into a ProviderConfig
is the composition root's job (main.py / a future core/startup_validation
step), e.g.:

    from core.config import get_config
    from providers.base_provider import ProviderConfig
    from providers.openai_provider import OpenAIProvider

    app_config = get_config()
    provider_config = ProviderConfig(
        api_key=app_config.providers.get_key("openai"),
        model=app_config.providers.model,
        extra={
            "timeout_seconds": app_config.providers.timeout_seconds,
            "base_url": app_config.providers.ollama_base_url
                if False else None,  # OpenAI has no per-provider base_url
                                      # field yet in ProviderConfig; add one
                                      # (e.g. openai_base_url) if/when needed.
        },
    )
    provider = OpenAIProvider()
    provider.initialize(provider_config)
    registry.register("openai", provider)

That wiring is intentionally NOT included in this file or in this task —
it belongs to whichever module core/config.py names as the allowed
dependency bridge, so it can be reviewed on its own.

MAFS alignment:
    - Chapter 2  (Transparency / Fail-Fast): initialize() validates
      api_key and model eagerly and raises immediately if either is
      missing — never a silent default, never a lazy failure on first use.
    - Chapter 7  (Tool Rules): input/output schema (ProviderConfig /
      ProviderResponse) was declared in base_provider.py before this file
      existed; this file only fills in behavior.
    - Chapter 9  (Coding Standard): AI-generated code, tagged below;
      snake_case functions, PascalCase class, full type hints and
      docstrings.
    - Chapter 10 (Security): the API key is read once from ProviderConfig,
      handed straight to the OpenAI SDK client constructor, and never
      logged, printed, or interpolated into any exception message.

# AI-generated
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Optional

from openai import OpenAI
from openai import OpenAIError as OpenAISDKError

from providers.base_provider import BaseProvider, ProviderConfig, ProviderResponse
from providers.exceptions import (
    ProviderConfigurationError,
    ProviderInitializationError,
    ProviderRequestError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    BaseProvider implementation backed by the official `openai` SDK.

    Lifecycle::

        provider = OpenAIProvider()
        provider.initialize(provider_config)   # builds the reusable client
        response = provider.generate("Hello there")
        provider.close()

    Instances are not thread-safe to re-initialize concurrently, but the
    underlying OpenAI SDK client is safe to reuse across many sequential
    generate() calls — initialize() is intended to run once per instance.
    """

    #: Registry key this provider is expected to be registered under.
    #: Also used as ProviderResponse.provider_name so callers can tell
    #: which provider produced a given response without inspecting `raw`.
    PROVIDER_NAME: ClassVar[str] = "openai"

    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None
        self._model: Optional[str] = None
        self._initialized: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle: initialize
    # ------------------------------------------------------------------ #

    def initialize(self, config: ProviderConfig) -> None:
        """
        Build the reusable OpenAI SDK client from the given ProviderConfig.

        Args:
            config: Must have `api_key` and `model` set. Optional
                `extra["timeout_seconds"]` (float) and `extra["base_url"]`
                (str) are forwarded to the SDK client verbatim; when
                absent, the SDK's own defaults apply — this file never
                hardcodes a timeout or base URL.

        Raises:
            ProviderConfigurationError: If `config.api_key` or
                `config.model` is missing.
            ProviderInitializationError: If the SDK client cannot be
                constructed (e.g. malformed base_url).
        """
        if not config.api_key:
            raise ProviderConfigurationError(
                "OpenAIProvider.initialize() requires ProviderConfig.api_key "
                "to be set. Populate OPENAI_API_KEY and route it into the "
                "ProviderConfig passed to initialize()."
            )
        if not config.model:
            raise ProviderConfigurationError(
                "OpenAIProvider.initialize() requires ProviderConfig.model "
                "to be set. Set the desired OpenAI model (e.g. 'gpt-4o') "
                "and route it into the ProviderConfig passed to "
                "initialize()."
            )

        timeout = config.extra.get("timeout_seconds")
        base_url = config.extra.get("base_url")

        try:
            self._client = OpenAI(
                api_key=config.api_key,
                base_url=base_url,  # None -> SDK default
                timeout=timeout,  # None -> SDK default
            )
        except OpenAISDKError as exc:
            raise ProviderInitializationError(
                f"Failed to initialize OpenAI client: {exc}"
            ) from exc

        self._model = config.model
        self._initialized = True
        logger.info(
            "OpenAIProvider initialized (model=%s, base_url=%s, timeout=%s)",
            self._model,
            base_url or "sdk-default",
            timeout if timeout is not None else "sdk-default",
        )

    # ------------------------------------------------------------------ #
    # Lifecycle: generate
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str, **kwargs: Any) -> ProviderResponse:
        """
        Generate a completion for `prompt` via the OpenAI Chat Completions
        API.

        Args:
            prompt: The user's input text.
            **kwargs: Forwarded verbatim to
                `client.chat.completions.create()` — e.g. temperature,
                max_tokens. Left open so new generation parameters never
                require a signature change here.

        Returns:
            ProviderResponse with `content` set to the first choice's
            message text and `raw` set to the untouched SDK response
            object (for debugging only — Core Engine code must not depend
            on its shape).

        Raises:
            ProviderInitializationError: If called before initialize().
            ProviderRequestError: If the underlying SDK call fails.
        """
        self._require_initialized()

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
        except OpenAISDKError as exc:
            raise ProviderRequestError(
                f"OpenAIProvider.generate() failed: {exc}"
            ) from exc

        content = completion.choices[0].message.content or ""
        return ProviderResponse(
            content=content,
            provider_name=self.PROVIDER_NAME,
            raw=completion,
        )

    # ------------------------------------------------------------------ #
    # Lifecycle: health_check
    # ------------------------------------------------------------------ #

    def health_check(self) -> bool:
        """
        Verify the provider is reachable and usable.

        Uses `models.list()` rather than a real chat completion so a
        health check never consumes generation tokens or costs money.

        Returns:
            bool: True if the client is initialized and the API responded
                without error; False otherwise. Never raises — callers
                (e.g. a future fallback-selection feature in
                ProviderManager) can treat this as a plain boolean signal.
        """
        if not self._initialized or self._client is None:
            return False
        try:
            self._client.models.list()
            return True
        except OpenAISDKError as exc:
            logger.warning("OpenAIProvider.health_check() failed: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    # Lifecycle: close
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """
        Release the underlying OpenAI SDK client's connection resources.

        Safe to call multiple times and safe to call even if initialize()
        was never called (no-op in that case).
        """
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "OpenAIProvider.close() raised while closing the "
                    "underlying client: %s",
                    exc,
                )
            finally:
                self._client = None
                self._initialized = False

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_initialized(self) -> None:
        """
        Guard used by every method that depends on a live client.

        Raises:
            ProviderInitializationError: If initialize() has not
                successfully run yet.
        """
        if not self._initialized or self._client is None:
            raise ProviderInitializationError(
                "OpenAIProvider method called before initialize(). "
                "Call initialize(config) first."
            )
