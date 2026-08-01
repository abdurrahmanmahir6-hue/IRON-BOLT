"""
providers/gemini/constants.py

Static provider metadata for the Gemini provider package.
Gemini Provider Refactor — Capability, Constants & Mapper extraction.

Design summary
---------------
This module owns all provider-specific constants that previously lived
inside GeminiProvider. Keeping them here ensures:

- GeminiProvider remains a thin lifecycle / SDK adapter.
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

PROVIDER_NAME: str = "gemini"
"""Canonical provider identifier used in ProviderResponse and registry
lookups. Matches the former GeminiProvider.PROVIDER_NAME ClassVar."""

DISPLAY_NAME: str = "Google Gemini"
"""Human-readable name for logs, UI, and error messages."""

SDK_IDENTIFIER: str = "google-genai"
"""Preferred Python package / SDK name that this adapter wraps.
Falls back to legacy ``google-generativeai`` when the new SDK is absent."""

LEGACY_SDK_IDENTIFIER: str = "google-generativeai"
"""Legacy Gemini SDK package name (google-generativeai)."""

# ------------------------------------------------------------------ #
# Defaults
# ------------------------------------------------------------------ #

DEFAULT_MODEL: str = "gemini-2.0-flash"
"""Default model when ProviderConfig.model is omitted by the caller.
The provider still requires an explicit model at initialize() time;
this constant is the recommended fallback for higher-level factories."""

DEFAULT_TIMEOUT_SECONDS: float = 60.0
"""Recommended default request timeout for Gemini SDK clients."""

DEFAULT_BASE_URL: str | None = None
"""Default base URL. None means the official Google AI endpoint.
Override via ProviderConfig.extra when targeting Vertex AI or proxies."""