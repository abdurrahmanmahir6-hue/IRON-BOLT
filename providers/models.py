"""
providers/models.py

Data models for the Provider Layer.
These models define the contract between Application/Core Engine and Providers.

Design principles:
- Dataclass-based for clarity and serialization support
- Immutable where possible (frozen=True for config)
- Clear defaults for optional fields
- No provider-specific SDKs imported here
"""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, List
from enum import Enum


class ProviderCapability(str, Enum):
    """Enumeration of provider capabilities."""
    TEXT_GENERATION = "text_generation"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """
    Configuration object passed to Provider.initialize().
    
    Contains all required and optional settings for a provider instance.
    This is the ONLY way providers receive configuration — no global state,
    no environment variable reading.
    """
    api_key: str
    model: str
    extra: Mapping[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate critical fields on construction."""
        if not self.api_key:
            raise ValueError("ProviderConfig.api_key cannot be empty")
        if not self.model:
            raise ValueError("ProviderConfig.model cannot be empty")


@dataclass(slots=True)
class ProviderRequest:
    """
    Unified request object for all providers.
    
    Carries the user's input and common parameters.
    Provider-specific extras go in the `extra` dict.
    """
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    extra: Mapping[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Basic validation."""
        if not self.prompt:
            raise ValueError("ProviderRequest.prompt cannot be empty")


@dataclass(slots=True)
class ProviderResponse:
    """
    Unified response object from all providers.
    
    Contains the generated content and metadata for tracing.
    The `raw` field is for debugging only — Core Engine code must NOT
    depend on its shape (provider-specific SDK response object).
    """
    content: str
    provider_name: str
    raw: Any = None  # Untouched SDK response object
    finish_reason: Optional[str] = None
    usage: Optional[Mapping[str, int]] = None
    
    def __post_init__(self) -> None:
        """Validate critical fields."""
        if not self.content:
            raise ValueError("ProviderResponse.content cannot be empty")
        if not self.provider_name:
            raise ValueError("ProviderResponse.provider_name cannot be empty")


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """
    Static metadata and capability set for a provider.
    
    Allows the Core Engine to discover capabilities without
    hard-coding provider names or inspection.
    """
    name: str
    display_name: str
    description: str
    capabilities: List[ProviderCapability] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    
    def supports_capability(self, capability: ProviderCapability) -> bool:
        """Check if this provider supports a given capability."""
        return capability in self.capabilities
