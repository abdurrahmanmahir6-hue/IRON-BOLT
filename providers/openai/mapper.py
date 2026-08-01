"""
providers/openai/mapper.py

Pure data-conversion layer for the OpenAI provider. Sprint 3 Task 5
(AR1 Redesign) — Phase 2 (OpenAI Mapper Extraction) + Phase 3
(Provider Metadata & Capability Extraction).

Design summary
---------------
OpenAIMapper is solely responsible for translating between the Core's
provider-agnostic contracts (ProviderRequest / ProviderResponse) and the
OpenAI SDK's request/response shapes. It is stateless and performs no
I/O: it never calls the SDK, never touches the client lifecycle, and
never logs. All of that remains OpenAIProvider's responsibility.

- to_sdk_request():      ProviderRequest -> OpenAI SDK request payload.
- to_provider_response(): OpenAI SDK response -> ProviderResponse.

Phase 3 note:
    Provider identity (`provider=` field on ProviderResponse) is taken
    from constants.PROVIDER_NAME so no hardcoded provider string remains
    in the conversion layer.

IB-AR alignment:
    - Chapter 2  (Transparency / Fail-Fast): to_provider_response()
      rejects an empty/choice-less completion immediately rather than
      letting a malformed ProviderResponse propagate downstream.
    - Chapter 7  (Tool Rules): implements the ProviderRequest /
      ProviderResponse conversion contracts exclusively.
    - Chapter 9  (Coding Standard): AI-generated, snake_case,
      PascalCase, full type hints.

"""

from __future__ import annotations

from typing import Any

from providers.models.provider_request import ProviderRequest
from providers.models.provider_response import ProviderResponse
from providers.exceptions import ProviderRequestError
from providers.openai.constants import PROVIDER_NAME


class OpenAIMapper:
    """
    Stateless converter between provider-agnostic contracts and the
    OpenAI SDK's request/response shapes.

    Data conversion only — no SDK calls, no client/runtime state, no
    logging. Exception translation for SDK-level failures still
    belongs to the external Translator layer; the one exception raised
    here (`ProviderRequestError` on an empty completion) is a data-
    integrity guard on the conversion itself, not SDK error handling.
    """

    # ------------------------------------------------------------------ #
    # Request conversion: ProviderRequest -> OpenAI SDK request payload
    # ------------------------------------------------------------------ #

    def to_sdk_request(self, request: ProviderRequest) -> dict[str, Any]:
        """
        Convert a ProviderRequest into the kwargs expected by
        `client.chat.completions.create()`.

        `model` is intentionally excluded: it is provider runtime state
        set at initialize()-time, not per-request data, and is supplied
        by OpenAIProvider itself when it calls the SDK.
        """
        payload: dict[str, Any] = {"messages": self._build_messages(request)}
        payload.update(self._build_kwargs(request))
        return payload

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

    # ------------------------------------------------------------------ #
    # Response conversion: OpenAI SDK response -> ProviderResponse
    # ------------------------------------------------------------------ #

    def to_provider_response(
        self, completion: Any, latency: float, request_id: str
    ) -> ProviderResponse:
        """
        Map an OpenAI SDK ChatCompletion object to a ProviderResponse.

        `latency` and `request_id` are call-lifecycle metadata owned by
        OpenAIProvider (timing and correlation-id generation are not
        data-conversion concerns) and are threaded through as-is; the
        final `request_id` still prefers the SDK's own completion.id,
        matching the original behavior exactly.
        """
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
            provider=PROVIDER_NAME,
            usage=usage,
            finish_reason=choice.finish_reason,
            latency=latency,
            request_id=completion.id or request_id,
            raw_response=completion,
        )