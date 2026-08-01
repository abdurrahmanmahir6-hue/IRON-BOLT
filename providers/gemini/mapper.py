"""
providers/gemini/mapper.py

Pure data-conversion layer for the Gemini provider.
Gemini Provider Refactor — Capability, Constants & Mapper extraction.

Design summary
---------------
GeminiMapper is solely responsible for translating between the provider's
call-site data (prompt + kwargs) and the Gemini SDK request/response
shapes. It is stateless and performs no I/O: it never calls the SDK,
never touches the client lifecycle, and never logs. All of that remains
GeminiProvider's responsibility.

- to_new_sdk_request():   prompt + model + kwargs -> new google-genai kwargs
- to_legacy_sdk_request(): prompt + kwargs -> (args, kwargs) for legacy SDK
- to_provider_response():  Gemini SDK response -> ProviderResponse

The public generate(prompt, **kwargs) signature is preserved; the mapper
accepts the same inputs the provider historically passed straight to the
SDK so runtime behaviour is unchanged.

IB-AR alignment:
    - Chapter 7  (Tool Rules): conversion contracts exclusively.
    - Chapter 9  (Coding Standard): snake_case, PascalCase, full type hints.
"""

from __future__ import annotations

from typing import Any

from providers.base_provider import ProviderResponse
from providers.gemini.constants import PROVIDER_NAME


class GeminiMapper:
    """
    Stateless converter between call-site data and Gemini SDK
    request/response shapes.

    Data conversion only — no SDK calls, no client/runtime state, no
    logging. Exception translation remains outside this layer.
    """

    # ------------------------------------------------------------------ #
    # Request conversion
    # ------------------------------------------------------------------ #

    def to_new_sdk_request(
        self,
        prompt: str,
        model: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build the keyword arguments expected by
        ``client.models.generate_content()`` (google-genai).

        Mirrors the historical inline call:

            client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=kwargs,
            )
        """
        return {
            "model": model,
            "contents": prompt,
            "config": kwargs,
        }

    def to_legacy_sdk_request(
        self,
        prompt: str,
        kwargs: dict[str, Any],
    ) -> tuple[tuple[Any, ...], dict[str, Any]]:
        """
        Build the positional / keyword arguments expected by
        ``GenerativeModel.generate_content()`` (google-generativeai).

        Mirrors the historical inline call:

            client.generate_content(prompt, **kwargs)

        Returns
        -------
        (args, kwargs)
            ``args`` is the positional tuple ``(prompt,)``;
            ``kwargs`` is passed through unchanged.
        """
        return (prompt,), dict(kwargs)

    # ------------------------------------------------------------------ #
    # Response conversion
    # ------------------------------------------------------------------ #

    def to_provider_response(self, response: Any) -> ProviderResponse:
        """
        Map a Gemini SDK response object to a ProviderResponse.

        Extracts ``response.text`` exactly as the historical provider did
        so runtime behaviour is unchanged.
        """
        content = response.text

        return ProviderResponse(
            content=content,
            provider_name=PROVIDER_NAME,
            raw=response,
        )