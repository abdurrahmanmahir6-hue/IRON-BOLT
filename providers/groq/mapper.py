"""
providers/groq/mapper.py

Pure data-conversion layer for the Groq provider.
IRON-BOLT Provider Layer — Groq Capability, Constants & Mapper extraction.

Design summary
---------------
GroqMapper is solely responsible for translating between the provider's
call-site data (prompt + kwargs) and the Groq SDK request/response
shapes. It is stateless and performs no I/O: it never calls the SDK,
never touches the client lifecycle, and never logs. All of that remains
GroqProvider's responsibility.

- to_sdk_request():      prompt + model + kwargs -> chat.completions.create kwargs
- to_provider_response(): Groq SDK completion -> ProviderResponse

The public generate(prompt, **kwargs) signature is preserved; the mapper
accepts the same inputs the provider historically passed straight to the
SDK so runtime behaviour is unchanged.

The Groq Python SDK mirrors the OpenAI client shape
(``client.chat.completions.create()``), so request construction follows
that contract while still matching the historical GroqProvider inline call.

IB-AR alignment:
    - Chapter 7  (Tool Rules): conversion contracts exclusively.
    - Chapter 9  (Coding Standard): snake_case, PascalCase, full type hints.
"""

from __future__ import annotations

from typing import Any

from providers.base_provider import ProviderResponse
from providers.groq.constants import PROVIDER_NAME


class GroqMapper:
    """
    Stateless converter between call-site data and Groq SDK
    request/response shapes.

    Data conversion only — no SDK calls, no client/runtime state, no
    logging. Exception translation remains outside this layer.
    """

    # ------------------------------------------------------------------ #
    # Request conversion
    # ------------------------------------------------------------------ #

    def to_sdk_request(
        self,
        prompt: str,
        model: str,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build the keyword arguments expected by
        ``client.chat.completions.create()``.

        Mirrors the historical inline call:

            client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

        ``model`` is supplied by the provider (runtime state set at
        initialize()-time). Extra generation parameters in *kwargs*
        (temperature, max_completion_tokens, stream, tools, …) are
        forwarded verbatim.
        """
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }

    # ------------------------------------------------------------------ #
    # Response conversion
    # ------------------------------------------------------------------ #

    def to_provider_response(self, completion: Any) -> ProviderResponse:
        """
        Map a Groq SDK ChatCompletion object to a ProviderResponse.

        Extracts the first choice's message text exactly as the
        historical provider did so runtime behaviour is unchanged.
        """
        content = completion.choices[0].message.content or ""

        return ProviderResponse(
            content=content,
            provider_name=PROVIDER_NAME,
            raw=completion,
        )