"""
providers/translators/openai.py

OpenAI SDK exception → framework Provider exception translator.
Sprint 3 Task 5 (AR1 Redesign) — Phase 4 (Translator Layer).

Design summary
---------------
OpenAIExceptionTranslator is the *only* module in the codebase that is
allowed to import and inspect concrete ``openai.*`` exception types.
Every other layer (ProviderManager, Registry, Core Engine) sees only
framework Provider exceptions.

Mapping (SDK → Framework)
-------------------------
AuthenticationError          → ProviderAuthenticationError
PermissionDeniedError        → ProviderAuthenticationError
RateLimitError               → ProviderRateLimitError
APIConnectionError           → ProviderNetworkError
APITimeoutError              → ProviderTimeoutError
BadRequestError              → ProviderBadRequestError
NotFoundError                → ProviderBadRequestError
ConflictError                → ProviderBadRequestError
UnprocessableEntityError     → ProviderBadRequestError
InternalServerError          → ProviderInternalError
APIStatusError (other 5xx)   → ProviderInternalError
APIStatusError (other 4xx)   → ProviderBadRequestError
APIResponseValidationError   → ProviderRequestError
APIError / OpenAIError       → ProviderRequestError
anything else                → ProviderRequestError

Already-framework exceptions are passed through unchanged so that
ProviderConfigurationError / ProviderInitializationError raised by the
provider itself are never double-wrapped.

IB-AR alignment:
    - Chapter 2  (Transparency / Fail-Fast): every SDK failure becomes a
      typed, inspectable Provider exception.
    - Chapter 7  (Tool Rules): pure mapping; no SDK calls, no lifecycle.
    - Chapter 9  (Coding Standard): full type hints, exhaustive mapping.
"""

from __future__ import annotations

import openai

from providers.exceptions import (
    ProviderAuthenticationError,
    ProviderBadRequestError,
    ProviderInternalError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from providers.translators.base import BaseExceptionTranslator


class OpenAIExceptionTranslator(BaseExceptionTranslator):
    """
    Translate OpenAI SDK exceptions into framework Provider exceptions.

    Stateless and side-effect free. The provider catches raw exceptions
    and re-raises whatever this translator returns.
    """

    def translate(self, exception: Exception) -> Exception:
        """
        Map *exception* to the corresponding framework exception.

        Framework Provider exceptions are returned as-is so that errors
        raised by the provider itself (config / init guards) are not
        re-wrapped.
        """
        # Pass through exceptions that already belong to the framework.
        if self._is_framework_exception(exception):
            return exception

        # --- Authentication / authorization ---------------------------------
        if isinstance(
            exception,
            (openai.AuthenticationError, openai.PermissionDeniedError),
        ):
            return ProviderAuthenticationError(str(exception))

        # --- Rate limiting --------------------------------------------------
        if isinstance(exception, openai.RateLimitError):
            return ProviderRateLimitError(str(exception))

        # --- Network / transport --------------------------------------------
        if isinstance(exception, openai.APIConnectionError):
            return ProviderNetworkError(str(exception))

        # --- Timeouts -------------------------------------------------------
        if isinstance(exception, openai.APITimeoutError):
            return ProviderTimeoutError(str(exception))

        # --- Client errors (4xx family) -------------------------------------
        if isinstance(
            exception,
            (
                openai.BadRequestError,
                openai.NotFoundError,
                openai.ConflictError,
                openai.UnprocessableEntityError,
            ),
        ):
            return ProviderBadRequestError(str(exception))

        # --- Server errors (5xx) --------------------------------------------
        if isinstance(exception, openai.InternalServerError):
            return ProviderInternalError(str(exception))

        # --- Generic status-error fallback (covers remaining 4xx/5xx) -------
        if isinstance(exception, openai.APIStatusError):
            status = getattr(exception, "status_code", None)
            if status is not None and 500 <= status < 600:
                return ProviderInternalError(str(exception))
            return ProviderBadRequestError(str(exception))

        # --- Validation / generic OpenAI errors -----------------------------
        if isinstance(
            exception,
            (openai.APIResponseValidationError, openai.APIError, openai.OpenAIError),
        ):
            return ProviderRequestError(str(exception))

        # --- Unknown --------------------------------------------------------
        return ProviderRequestError(str(exception))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_framework_exception(exception: Exception) -> bool:
        """
        Return True when *exception* originates from the providers package
        (i.e. it is already a framework exception and must not be wrapped).
        """
        module = type(exception).__module__ or ""
        return module.startswith("providers.")