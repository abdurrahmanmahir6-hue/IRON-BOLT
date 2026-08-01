"""
providers/groq/constants.py

Static provider metadata for the Groq provider package.
IRON-BOLT Provider Layer — Groq Capability, Constants & Mapper extraction.

Design summary
---------------
This module owns all provider-specific constants that previously lived
inside GroqProvider. Keeping them here ensures:

- GroqProvider remains a thin lifecycle / SDK adapter.
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

PROVIDER_NAME: str = "groq"
"""Canonical provider identifier used in ProviderResponse and registry
lookups. Matches the former GroqProvider.PROVIDER_NAME ClassVar."""

DISPLAY_NAME: str = "Groq"
"""Human-readable name for logs, UI, and error messages."""

SDK_IDENTIFIER: str = "groq"
"""Python package / SDK name that this adapter wraps."""

# ------------------------------------------------------------------ #
# Defaults
# ------------------------------------------------------------------ #

DEFAULT_MODEL: str = "openai/gpt-oss-120b"
"""Default model when ProviderConfig.model is omitted by the caller.
The provider still requires an explicit model at initialize() time;
this constant is the recommended fallback for higher-level factories
(matches core/config.py's historical Groq default)."""

DEFAULT_TIMEOUT_SECONDS: float = 60.0
"""Recommended default request timeout for the Groq SDK client when
ProviderConfig.extra does not supply timeout_seconds."""

DEFAULT_BASE_URL: str | None = None
"""Default base_url for the Groq SDK. None means the official Groq
endpoint. Override via ProviderConfig.extra["base_url"] for proxy or
self-hosted scenarios."""