"""
providers/openai/constants.py

Static provider metadata for the OpenAI provider package.
Sprint 3 Task 5 (AR1 Redesign) — Phase 3 (Provider Metadata &
Capability Extraction).

Design summary
---------------
This module owns all provider-specific constants that previously lived
inside OpenAIProvider. Keeping them here ensures:

- OpenAIProvider remains a thin lifecycle / SDK adapter.
- Metadata is importable by registry, health, and documentation layers
  without instantiating the provider.
- No hardcoded string literals remain in provider.py.

IB-AR alignment:
    - Chapter 7  (Tool Rules): pure data; no business logic.
    - Chapter 9  (Coding Standard): snake_case constants, full docs.
    - Chapter 10 (Security): no secrets; API keys stay in config only.
"""

from __future__ import annotations

# ------------------------------------------------------------------ #
# Identity
# ------------------------------------------------------------------ #

PROVIDER_NAME: str = "openai"
"""Canonical provider identifier used in ProviderResponse.provider and
registry lookups."""

DISPLAY_NAME: str = "OpenAI"
"""Human-readable name for logs, UI, and error messages."""

SDK_IDENTIFIER: str = "openai"
"""Python package / SDK name that this adapter wraps."""

# ------------------------------------------------------------------ #
# Defaults
# ------------------------------------------------------------------ #

DEFAULT_MODEL: str = "gpt-5.5"
"""Default model when ProviderConfig.model is omitted by the caller.
The provider still requires an explicit model at initialize() time;
this constant is the recommended fallback for higher-level factories."""

DEFAULT_TIMEOUT_SECONDS: float = 60.0
"""Default request timeout passed to the OpenAI SDK client when
ProviderConfig.extra does not supply timeout_seconds."""

DEFAULT_BASE_URL: str | None = None
"""Default base_url for the OpenAI SDK. None means the official
OpenAI endpoint (https://api.openai.com/v1). Override via
ProviderConfig.extra["base_url"] for Azure / proxy endpoints."""
