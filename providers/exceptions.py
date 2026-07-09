"""
providers/exceptions.py

Provider-agnostic exception hierarchy.

Sprint 3 Task 5 introduces the first concrete provider (OpenAIProvider),
which is also the first code in providers/ that needs to raise errors.
Rather than let OpenAIProvider raise raw `openai.OpenAIError` (or a future
GeminiProvider raise a Gemini-specific SDK exception) past its own
boundary, every concrete provider raises these shared types instead.

This is what keeps ProviderManager / the Orchestrator provider-agnostic
at the exception level, not just the return-type level:

    try:
        response = provider.generate(prompt)
    except ProviderRequestError:
        ...  # no `import openai`, `import google.genai`, etc. needed here

MAFS alignment:
    - Chapter 2  (Transparency / Fail-Fast): every failure is specific and
      actionable; nothing is silently swallowed or defaulted.
    - Chapter 9  (Coding Standard / OCP): this file is shared across all of
      providers/, so adding GeminiProvider, ClaudeProvider, etc. in later
      sprints never requires inventing a new exception vocabulary or
      modifying this file.
    - Chapter 10 (Security): no exception message in this module — or in
      any provider that raises these — should ever interpolate a secret
      value (API key, token). Provider implementations are responsible for
      keeping messages free of secrets; see OpenAIProvider for the pattern.

# AI-generated
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider-layer errors. Catch this to handle any
    provider failure generically, regardless of which concrete provider
    raised it."""


class ProviderConfigurationError(ProviderError):
    """Raised when a ProviderConfig handed to initialize() is missing a
    required field (api_key, model, ...) or contains an invalid value.

    Always raised at initialize()-time, never at generate()-time — this is
    what makes provider misconfiguration fail fast instead of surfacing as
    a confusing error on the first real request.
    """


class ProviderInitializationError(ProviderError):
    """Raised when a provider's underlying SDK client cannot be
    constructed, or when a method that requires initialize() to have
    already run (generate, health_check) is called before it has."""


class ProviderRequestError(ProviderError):
    """Raised when a call to the underlying provider SDK fails at request
    time — network error, API error, rate limit, timeout, etc."""
