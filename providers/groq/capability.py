"""
providers/groq/capability.py

Capability metadata for the Groq provider.
IRON-BOLT Provider Layer — Groq Capability, Constants & Mapper extraction.

Design summary
---------------
GROQ_CAPABILITIES is the single source of truth for what the Groq
adapter supports. GroqProvider.get_capabilities() simply returns this
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

GROQ_CAPABILITIES: tuple[ProviderCapability, ...] = (
    ProviderCapability.CHAT,
    ProviderCapability.TOOL_CALLING,
    ProviderCapability.STREAMING,
    ProviderCapability.JSON_MODE,
)
"""Ordered, immutable set of capabilities supported by GroqProvider.

Registry and routing layers import this constant directly so they can
inspect support without constructing a provider instance.

Notes
-----
- TOOL_CALLING covers Groq function-calling / tool use on chat models.
- JSON_MODE covers response_format / structured JSON generation.
- VISION, EMBEDDINGS, and REASONING are intentionally omitted: not all
  Groq-hosted models expose those channels; include them only when a
  specific model family is guaranteed to support them.
"""