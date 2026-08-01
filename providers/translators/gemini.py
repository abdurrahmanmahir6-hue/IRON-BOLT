"""
providers/translators/gemini.py

Gemini SDK exception → framework Provider exception translator.
IRON-BOLT Provider Layer — Gemini Translator Implementation.

Design summary
---------------
GeminiExceptionTranslator is the *only* module in the codebase that is
allowed to import and inspect concrete Gemini / Google API exception
types. Every other layer (ProviderManager, Registry, Core Engine) sees
only framework Provider exceptions.

Supports both SDK families used by GeminiProvider:

- google-genai          (new)
- google-generativeai   (legacy)
- google.api_core       (shared transport errors)

Mapping (SDK → Framework)
-------------------------
Unauthenticated / AuthenticationError
        → ProviderAuthenticationError
PermissionDenied / PermissionDeniedError
        → ProviderAuthorizationError
ResourceExhausted / ResourceExhaustedError
        → ProviderRateLimitError
DeadlineExceeded / DeadlineExceededError
        → ProviderTimeoutError
ServiceUnavailable / UnavailableError / Aborted
        → ProviderNetworkError
InvalidArgument / InvalidArgumentError / FailedPrecondition /
NotFound / AlreadyExists / OutOfRange / BadRequest
        → ProviderBadRequestError
InternalServerError / InternalServerError (api_core) / DataLoss /
Unknown / ServerError
        → ProviderInternalError
ClientError (genai) without a more specific match
        → ProviderBadRequestError
APIError / GoogleAPIError / GoogleAPICallError
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

from typing import Any

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
# module itself remains importable even when neither Gemini SDK is installed.
# ---------------------------------------------------------------------------

_API_CORE_TYPES: dict[str, type] = {}
_GENAI_TYPES: dict[str, type] = {}

try:
    from google.api_core import exceptions as _api_core_exc

    for _name in (
        "Unauthenticated",
        "PermissionDenied",
        "ResourceExhausted",
        "DeadlineExceeded",
        "ServiceUnavailable",
        "Aborted",
        "InvalidArgument",
        "FailedPrecondition",
        "NotFound",
        "AlreadyExists",
        "OutOfRange",
        "BadRequest",
        "InternalServerError",
        "DataLoss",
        "Unknown",
        "GoogleAPIError",
        "GoogleAPICallError",
        "RetryError",
        "Cancelled",
    ):
        _cls = getattr(_api_core_exc, _name, None)
        if isinstance(_cls, type):
            _API_CORE_TYPES[_name] = _cls
except ImportError:
    pass

try:
    from google.genai import errors as _genai_errors

    for _name in ("APIError", "ClientError", "ServerError"):
        _cls = getattr(_genai_errors, _name, None)
        if isinstance(_cls, type):
            _GENAI_TYPES[_name] = _cls
except ImportError:
    pass


def _types(*names: str) -> tuple[type, ...]:
    """Collect resolved exception classes by name from both registries."""
    found: list[type] = []
    for name in names:
        if name in _API_CORE_TYPES:
            found.append(_API_CORE_TYPES[name])
        if name in _GENAI_TYPES:
            found.append(_GENAI_TYPES[name])
    return tuple(found)


class GeminiExceptionTranslator(BaseExceptionTranslator):
    """
    Translate Gemini / Google API exceptions into framework Provider
    exceptions.

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
        auth_types = _types("Unauthenticated")
        if auth_types and isinstance(exception, auth_types):
            return ProviderAuthenticationError(str(exception))

        # --- Authorization --------------------------------------------------
        perm_types = _types("PermissionDenied")
        if perm_types and isinstance(exception, perm_types):
            return ProviderAuthorizationError(str(exception))

        # --- Rate limiting / quota ------------------------------------------
        rate_types = _types("ResourceExhausted")
        if rate_types and isinstance(exception, rate_types):
            return ProviderRateLimitError(str(exception))

        # --- Timeouts -------------------------------------------------------
        timeout_types = _types("DeadlineExceeded")
        if timeout_types and isinstance(exception, timeout_types):
            return ProviderTimeoutError(str(exception))

        # --- Network / availability -----------------------------------------
        network_types = _types("ServiceUnavailable", "Aborted", "Cancelled")
        if network_types and isinstance(exception, network_types):
            return ProviderNetworkError(str(exception))

        # --- Client / bad-request family ------------------------------------
        bad_req_types = _types(
            "InvalidArgument",
            "FailedPrecondition",
            "NotFound",
            "AlreadyExists",
            "OutOfRange",
            "BadRequest",
            "ClientError",
        )
        if bad_req_types and isinstance(exception, bad_req_types):
            return ProviderBadRequestError(str(exception))

        # --- Server / internal ----------------------------------------------
        internal_types = _types(
            "InternalServerError",
            "DataLoss",
            "Unknown",
            "ServerError",
        )
        if internal_types and isinstance(exception, internal_types):
            return ProviderInternalError(str(exception))

        # --- Generic Google / GenAI API errors ------------------------------
        generic_types = _types("APIError", "GoogleAPIError", "GoogleAPICallError", "RetryError")
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

        auth_names = {"Unauthenticated", "AuthenticationError", "AuthError"}
        authz_names = {"PermissionDenied", "PermissionDeniedError", "Forbidden"}
        rate_names = {"ResourceExhausted", "ResourceExhaustedError", "RateLimitError", "TooManyRequests"}
        timeout_names = {"DeadlineExceeded", "DeadlineExceededError", "TimeoutError", "APITimeoutError"}
        network_names = {
            "ServiceUnavailable",
            "UnavailableError",
            "Unavailable",
            "Aborted",
            "Cancelled",
            "ConnectionError",
            "APIConnectionError",
        }
        bad_req_names = {
            "InvalidArgument",
            "InvalidArgumentError",
            "FailedPrecondition",
            "NotFound",
            "NotFoundError",
            "AlreadyExists",
            "OutOfRange",
            "BadRequest",
            "BadRequestError",
            "ClientError",
            "BlockedPromptException",
            "StopCandidateException",
        }
        internal_names = {
            "InternalServerError",
            "DataLoss",
            "Unknown",
            "ServerError",
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