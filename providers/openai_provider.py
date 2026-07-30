"""    
providers/openai_provider.py    
    
Concrete BaseProvider implementation acting as a pure adapter for the    
official OpenAI Python SDK. Sprint 3 Task 5 (AR1 Redesign).    
    
Design summary (AR1 Redesign)    
-----------------------------    
OpenAIProvider implements the lifecycle declared by BaseProvider and acts    
strictly as an SDK adapter. It no longer handles exception translation,    
metadata duplication, or complex configuration parsing.    
    
- Input: ProviderRequest (containing messages, system_prompt, tools, etc.)    
- Output: ProviderResponse (containing usage, latency, finish_reason, etc.)    
- Capabilities: Exposes supported features via get_capabilities().    
- Exceptions: SDK exceptions (openai.OpenAIError) are allowed to bubble up    
  to the Translator layer, keeping the Core SDK-agnostic.    
    
IB-AR alignment:    
    - Chapter 2  (Transparency / Fail-Fast): initialize() validates    
      config eagerly.    
    - Chapter 7  (Tool Rules): strictly follows the new ProviderRequest/    
      ProviderResponse contracts.    
    - Chapter 9  (Coding Standard): AI-generated, snake_case, PascalCase,    
      full type hints.    
    - Chapter 10 (Security): API key is never logged or exposed.    
    
"""    
    
from __future__ import annotations    
    
import logging    
import time    
import uuid    
from typing import Any    
    
from openai import OpenAI    
    
from providers.base_provider import BaseProvider    
from providers.models.provider_config import ProviderConfig    
from providers.models.provider_request import ProviderRequest    
from providers.models.provider_response import ProviderResponse    
from providers.models.provider_capability import ProviderCapability    
from providers.exceptions import (    
    ProviderConfigurationError,    
    ProviderInitializationError,    
    ProviderRequestError,    
)    
    
logger = logging.getLogger(__name__)    
    
    
class OpenAIProvider(BaseProvider):    
    """    
    BaseProvider adapter for the official `openai` SDK.    
    
    This class is strictly an adapter. It translates ProviderRequest into    
    OpenAI SDK calls and maps the SDK response to ProviderResponse.    
    Exception translation is handled by the external Translator layer.    
    """    
    
    def __init__(self) -> None:    
        self._client: OpenAI | None = None    
        self._model: str | None = None    
        self._initialized: bool = False    
    
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
            "OpenAIProvider initialized | provider=openai | model=%s",    
            self._model,    
        )    
    
    def _validate_config(self, config: ProviderConfig) -> None:    
        """Validate required configuration parameters."""    
        if not config.api_key:    
            raise ProviderConfigurationError(    
                "OpenAIProvider.initialize() requires ProviderConfig.api_key "    
                "to be set."    
            )    
        if not config.model:    
            raise ProviderConfigurationError(    
                "OpenAIProvider.initialize() requires ProviderConfig.model "    
                "to be set."    
            )    
    
    def _create_client(self, config: ProviderConfig) -> OpenAI:    
        """Instantiate the OpenAI SDK client."""    
        timeout = config.extra.get("timeout_seconds")    
        base_url = config.extra.get("base_url")    
    
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
    
        messages = self._build_messages(request)    
        kwargs = self._build_kwargs(request)    
    
        request_id = str(uuid.uuid4())    
        start_time = time.perf_counter()    
    
        # SDK exceptions bubble up to the Translator layer    
        completion = self._client.chat.completions.create(    
            model=self._model,    
            messages=messages,    
            **kwargs,    
        )    
    
        latency = time.perf_counter() - start_time    
    
        logger.info(    
            "OpenAIProvider generate completed | provider=openai | model=%s | latency=%.4f | request_id=%s",    
            self._model,    
            latency,    
            request_id,    
        )    
    
        return self._build_response(completion, latency, request_id)    
    
    def _build_messages(self, request: ProviderRequest) -> list[dict[str, Any]]:    
        """Convert ProviderRequest into OpenAI's message format."""    
        messages: list[dict[str, Any]] = []    
    
        if request.system_prompt:    
            messages.append({"role": "system", "content": request.system_prompt})    
    
        if request.messages:    
            messages.extend(request.messages)    
        elif request.prompt:    
            if request.images:    
                content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]    
                for img in request.images:    
                    content.append({"type": "image_url", "image_url": {"url": img}})    
                messages.append({"role": "user", "content": content})    
            else:    
                messages.append({"role": "user", "content": request.prompt})    
    
        return messages    
    
    def _build_kwargs(self, request: ProviderRequest) -> dict[str, Any]:    
        """Extract generation parameters from ProviderRequest."""    
        kwargs: dict[str, Any] = {}    
        if request.temperature is not None:    
            kwargs["temperature"] = request.temperature    
        if request.max_tokens is not None:    
            kwargs["max_tokens"] = request.max_tokens    
        if request.stream is not None:    
            kwargs["stream"] = request.stream    
        if request.tools:    
            kwargs["tools"] = request.tools    
        return kwargs    
    
    def _build_response(    
        self, completion: Any, latency: float, request_id: str    
    ) -> ProviderResponse:    
        """Map OpenAI SDK response to ProviderResponse."""    
        if not completion or not completion.choices:    
            raise ProviderRequestError("OpenAIProvider received an empty response from the API.")    
    
        choice = completion.choices[0]    
        message = choice.message    
    
        usage = None    
        if completion.usage:    
            usage = {    
                "prompt_tokens": completion.usage.prompt_tokens,    
                "completion_tokens": completion.usage.completion_tokens,    
                "total_tokens": completion.usage.total_tokens,    
            }    
    
        return ProviderResponse(    
            content=message.content or "",    
            model=completion.model,    
            provider="openai",    
            usage=usage,    
            finish_reason=choice.finish_reason,    
            latency=latency,    
            request_id=completion.id or request_id,    
            raw_response=completion,    
        )    
    
    # ------------------------------------------------------------------ #    
    # Capabilities    
    # ------------------------------------------------------------------ #    
    
    def get_capabilities(self) -> list[ProviderCapability]:    
        """    
        Return the list of capabilities supported by this provider.    
        Registry uses this to route requests intelligently.    
        """    
        return [    
            ProviderCapability.CHAT,    
            ProviderCapability.VISION,    
            ProviderCapability.TOOL_CALLING,    
            ProviderCapability.STREAMING,    
            ProviderCapability.JSON_MODE,    
            ProviderCapability.REASONING,    
            ProviderCapability.EMBEDDINGS,    
        ]    
    
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
            logger.warning("OpenAIProvider.health_check() failed: %s", exc)    
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
                logger.warning("OpenAIProvider.close() raised: %s", exc)    
    
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
                "OpenAI client is not initialized. Call initialize(config) first."    
            )    
    
    def _require_model(self) -> None:    
        """Guard to ensure the model is set."""    
        if not self._model:    
            raise ProviderInitializationError(    
                "OpenAI model is not set. Call initialize(config) first."    
            )  
