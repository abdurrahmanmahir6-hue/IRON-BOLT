"""
IRON BOLT - Provider Layer Exceptions

This module defines the standard exception hierarchy and error context for the Provider Layer.
All provider-related errors must inherit from ProviderError to ensure consistent error handling,
logging, and exception translation across the framework.

Clean Architecture Rule:
- This file MUST NOT import any provider-specific SDKs (openai, groq, google, etc.).
- Exception translation from SDK exceptions to ProviderError happens in the `translators/` module
  or directly inside the concrete Provider implementations.
- BaseProvider contract guarantees that NO SDK exceptions leak beyond the provider boundary.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Mapping


@dataclass(frozen=True, slots=True)
class ProviderErrorContext:
    """
    Structured metadata for provider exceptions.
    Using a dataclass ensures type safety, clear defaults, and easy serialization for logging.
    """
    provider_name: Optional[str] = None
    model: Optional[str] = None
    status_code: Optional[int] = None
    retry_after: Optional[float] = None
    is_retryable: bool = False
    raw_error: Optional[Exception] = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = []
        if self.provider_name:
            parts.append(f"provider={self.provider_name}")
        if self.model:
            parts.append(f"model={self.model}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.retry_after is not None:
            parts.append(f"retry_after={self.retry_after}s")
        if self.is_retryable:
            parts.append("retryable=True")
            
        return f"[{', '.join(parts)}]" if parts else ""


class ProviderError(Exception):
    """
    Base exception for all Provider Layer errors in IRON BOLT.
    
    Contract:
    - BaseProvider guarantees that NO provider-specific SDK exceptions will leak 
      beyond the provider boundary. They must be translated into ProviderError 
      or its subclasses.
    """
    
    def __init__(
        self, 
        message: str, 
        context: Optional[ProviderErrorContext] = None
    ) -> None:
        self.message = message
        self.context = context or ProviderErrorContext()
        
        # Build the final string for standard Exception
        full_message = message
        context_str = str(self.context)
        if context_str:
            full_message = f"{message} {context_str}"
            
        super().__init__(full_message)

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, context={self.context!r})"


# -----------------------------------------------------------------------------
# Configuration & Registry Errors
# -----------------------------------------------------------------------------

class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid, incomplete, or missing required fields."""
    pass


class ProviderNotFoundError(ProviderError):
    """
    Raised when a requested provider is not registered or available in the registry.
    (Replaces KeyError in registry.py)
    """
    pass


class ProviderAlreadyRegisteredError(ProviderError):
    """
    Raised when attempting to register a provider that already exists in the registry.
    (Replaces ValueError in registry.py)
    """
    pass


# -----------------------------------------------------------------------------
# Authentication & Authorization Errors
# -----------------------------------------------------------------------------

class ProviderAuthenticationError(ProviderError):
    """
    Raised when authentication with the provider fails.
    Examples: Invalid, missing, or expired API keys, Permission Denied.
    (Translates AuthenticationError, PermissionDenied, etc.)
    """
    pass


# -----------------------------------------------------------------------------
# Connection & Network Errors
# -----------------------------------------------------------------------------

class ProviderConnectionError(ProviderError):
    """
    Raised when a network-level or connection error occurs while reaching the provider API.
    (Translates APIConnectionError, NetworkError, etc.)
    """
    pass


class ProviderTimeoutError(ProviderError):
    """
    Raised when a request to the provider exceeds the configured timeout limit.
    (Translates APITimeoutError, DeadlineExceeded, etc.)
    """
    pass


class ProviderUnavailableError(ProviderError):
    """
    Raised when the provider service is down, unreachable, or failing health checks.
    (Translates 503 Service Unavailable, APIConnectionError, etc.)
    """
    pass


# -----------------------------------------------------------------------------
# Request & Response Errors
# -----------------------------------------------------------------------------

class ProviderInvalidRequestError(ProviderError):
    """
    Raised when the request payload to the provider is invalid, malformed, or rejected by the API.
    (Translates 400 Bad Request, InvalidRequestError, etc.)
    """
    pass


class ProviderResponseError(ProviderError):
    """
    Raised when the provider returns an invalid, unexpected, or unparsable response.
    (Translates 500 Internal Server Error, malformed JSON, etc.)
    """
    pass


class ProviderModelNotFoundError(ProviderError):
    """
    Raised when the requested model does not exist or is not supported by the provider.
    (Translates ModelNotFound, 404 Not Found for model endpoints, etc.)
    """
    pass


# -----------------------------------------------------------------------------
# Rate Limit & Quota Errors
# -----------------------------------------------------------------------------

class ProviderRateLimitError(ProviderError):
    """
    Raised when the provider's API rate limit is exceeded.
    (Translates RateLimitError, 429 Too Many Requests, ResourceExhausted, etc.)
    """
    pass


class ProviderQuotaExceededError(ProviderError):
    """
    Raised when the user's account quota (e.g., token limits, billing limits) is exceeded.
    (Translates InsufficientQuotaError, BillingLimitExceeded, etc.)
    """
    pass


# -----------------------------------------------------------------------------
# Internal / Catch-all Errors
# -----------------------------------------------------------------------------

class ProviderInternalError(ProviderError):
    """
    Raised for unexpected internal errors within the provider implementation or SDK.
    Used as a fallback when an SDK exception cannot be mapped to a specific category.
    """
    pass
