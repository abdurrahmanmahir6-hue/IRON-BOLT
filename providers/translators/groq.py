"""
providers/translators/groq.py

Groq SDK exception → framework Provider exception translator.
IRON-BOLT Provider Layer — Groq Translator Implementation.

Design summary
---------------
GroqExceptionTranslator is the *only* module in the codebase that is
allowed to import and inspect concrete ``groq.*`` exception types.
Every other layer (ProviderManager, Registry, Core Engine) sees only
framework Provider exceptions.

The Groq Python SDK follows the OpenAI client exception hierarchy, so
the mapping strategy mirrors ``OpenAIExceptionTranslator`` while still
distinguishing authentication from authorization where the SDK provides
separate types.

Mapping (SDK → Framework)
-------------------------
AuthenticationError
        → ProviderAuthenticationError
PermissionDeniedError
        → ProviderAuthorizationError
RateLimitError
        → ProviderRateLimitError
APIConnectionError
        → ProviderNetworkError
APITimeoutError
        → ProviderTimeoutError
BadRequestError
NotFoundError
ConflictError
UnprocessableEntityError
        → ProviderBadRequestError
InternalServerError
        → ProviderInternalError
APIStatusError (other 5xx)
        → ProviderInternalError
APIStatusError (other 4xx)
        → ProviderBadRequestError
APIResponseValidationError
APIError
GroqError
        → ProviderRequestError
anything else
        → ProviderRequestError

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

from providers.exceptions import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderBadRequestError,
    ProviderInternalError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from providers.translators.base import BaseExceptionTranslator

# ---------------------------------------------------------------------------
# Optional SDK exception types — resolved at import time so the translator
# module itself remains importable even when the Groq SDK is not installed.
# ---------------------------------------------------------------------------

_GROQ_TYPES: dict[str, type] = {}

try:
    import groq as _groq

    for _name in (
        "AuthenticationError",
        "PermissionDeniedError",
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "BadRequestError",
        "NotFoundError",
        "ConflictError",
        "UnprocessableEntityError",
        "InternalServerError",
        "APIStatusError",
        "APIResponseValidationError",
        "APIError",
        "GroqError",
    ):
        _cls = getattr(_groq, _name, None)
        if isinstance(_cls, type):
            _GROQ_TYPES[_name] = _cls
except ImportError:
    pass


def _types(*names: str) -> tuple[type, ...]:
    """Collect resolved Groq exception classes by name."""
    found: list[type] = []
    for name in names:
        if name in _GROQ_TYPES:
            found.append(_GROQ_TYPES[name])
    return tuple(found)


class GroqExceptionTranslator(BaseExceptionTranslator):
    """
    Translate Groq SDK exceptions into framework Provider exceptions.

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
        if self._is_framework_exception(exception):
            return exception

        # --- Authentication -------------------------------------------------
        auth_types = _types("AuthenticationError")
        if auth_types and isinstance(exception, auth_types):
            return ProviderAuthenticationError(str(exception))

        # --- Authorization --------------------------------------------------
        perm_types = _types("PermissionDeniedError")
        if perm_types and isinstance(exception, perm_types):
            return ProviderAuthorizationError(str(exception))

        # --- Rate limiting --------------------------------------------------
        rate_types = _types("RateLimitError")
        if rate_types and isinstance(exception, rate_types):
            return ProviderRateLimitError(str(exception))

        # --- Network / transport --------------------------------------------
        network_types = _types("APIConnectionError")
        if network_types and isinstance(exception, network_types):
            return ProviderNetworkError(str(exception))

        # --- Timeouts -------------------------------------------------------
        timeout_types = _types("APITimeoutError")
        if timeout_types and isinstance(exception, timeout_types):
            return ProviderTimeoutError(str(exception))

        # --- Client errors (4xx family) -------------------------------------
        bad_req_types = _types(
            "BadRequestError",
            "NotFoundError",
            "ConflictError",
            "UnprocessableEntityError",
        )
        if bad_req_types and isinstance(exception, bad_req_types):
            return ProviderBadRequestError(str(exception))

        # --- Server errors (5xx) --------------------------------------------
        internal_types = _types("InternalServerError")
        if internal_types and isinstance(exception, internal_types):
            return ProviderInternalError(str(exception))

        # --- Generic status-error fallback (covers remaining 4xx/5xx) -------
        status_types = _types("APIStatusError")
        if status_types and isinstance(exception, status_types):
            status = getattr(exception, "status_code", None)
            if status is not None and 500 <= status < 600:
                return ProviderInternalError(str(exception))
            return ProviderBadRequestError(str(exception))

        # --- Validation / generic Groq errors -------------------------------
        generic_types = _types("APIResponseValidationError", "APIError", "GroqError")
        if generic_types and isinstance(exception, generic_types):
            return ProviderRequestError(str(exception))

        # --- Name-based fallback (covers SDKs that raise non-class-matched
        #     errors or rename types across versions) ----------------------
        mapped = self._translate_by_name(exception)
        if mapped is not None:
            return mapped

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

    @staticmethod
    def _translate_by_name(exception: Exception) -> Exception | None:
        """
        Fallback mapping based on the exception class *name*.

        Useful when the concrete class object was not importable (SDK not
        installed in this process) but a serialized / re-raised error still
        carries a recognizable type name.
        """
        name = type(exception).__name__

        auth_names = {"AuthenticationError", "AuthError", "Unauthenticated"}
        authz_names = {"PermissionDeniedError", "PermissionDenied", "Forbidden"}
        rate_names = {"RateLimitError", "ResourceExhausted", "TooManyRequests"}
        timeout_names = {"APITimeoutError", "TimeoutError", "DeadlineExceeded"}
        network_names = {
            "APIConnectionError",
            "ConnectionError",
            "ServiceUnavailable",
            "Unavailable",
            "Aborted",
        }
        bad_req_names = {
            "BadRequestError",
            "BadRequest",
            "NotFoundError",
            "NotFound",
            "ConflictError",
            "Conflict",
            "UnprocessableEntityError",
            "InvalidRequestError",
            "InvalidArgument",
        }
        internal_names = {
            "InternalServerError",
            "InternalError",
            "ServerError",
            "DataLoss",
            "Unknown",
        }

        if name in auth_names:
            return ProviderAuthenticationError(str(exception))
        if name in authz_names:
            return ProviderAuthorizationError(str(exception))
        if name in rate_names:
            return ProviderRateLimitError(str(exception))
        if name in timeout_names:
            return ProviderTimeoutError(str(exception))
        if name in network_names:
            return ProviderNetworkError(str(exception))
        if name in bad_req_names:
            return ProviderBadRequestError(str(exception))
        if name in internal_names:
            return ProviderInternalError(str(exception))

        return None