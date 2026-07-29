from dataclasses import dataclass, field  
from typing import Any, Optional  
  
from providers.base_provider import BaseProvider  
from providers.provider_capability import ProviderCapability  
  
  
@dataclass(frozen=True)  
class ProviderInfo:  
    name: str  
    display_name: str  
  
    # Runtime object  
    provider: BaseProvider  
  
    # Static metadata  
    version: Optional[str] = None  
    description: str = ""  
  
    # Capabilities  
    capabilities: ProviderCapability = field(default_factory=ProviderCapability)  
  
    # Supported models  
    supported_models: tuple[str, ...] = ()  
  
    # Extra provider-specific metadata  
    metadata: dict[str, Any] = field(default_factory=dict)  