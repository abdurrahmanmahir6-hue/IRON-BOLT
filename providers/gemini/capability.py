"""
providers/gemini/capability.py

Capability metadata for the Gemini provider.
Gemini Provider Refactor — Capability, Constants & Mapper extraction.

Design summary
---------------
GEMINI_CAPABILITIES is the single source of truth for what the Gemini
adapter supports. GeminiProvider.get_capabilities() simply returns this
tuple; no capability logic lives inside the provider class.

This module contains only static declarations — no business logic,
no SDK calls, no Provider lifecycle code.

IB-AR alignment:
    - Chapter 7  (Tool Rules): pure metadata; Registry consumes it.
    - Chapter 9  (Coding Standard): UPPER_SNAKE for the constant,
      full type hints via the imported enum.
"""

from __future__ import annotations

from providers.models.provider_capability import ProviderCapability

GEMINI_CAPABILITIES: tuple[ProviderCapability, ...] = (
    ProviderCapability.CHAT,
    ProviderCapability.VISION,
    ProviderCapability.TOOL_CALLING,
    ProviderCapability.STREAMING,
    ProviderCapability.JSON_MODE,
    ProviderCapability.EMBEDDINGS,
)
"""Ordered, immutable set of capabilities supported by GeminiProvider.

Registry and routing layers import this constant directly so they can
inspect support without constructing a provider instance.

Notes
-----
- TOOL_CALLING covers Gemini function-calling / tool use.
- JSON_MODE covers structured-output / response-schema modes.
- REASONING is intentionally omitted: not all Gemini models expose a
  dedicated reasoning channel; include it only when a specific model
  family is guaranteed to support it.
"""