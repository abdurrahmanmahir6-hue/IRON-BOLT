"""  
provider_config.py  
  
Canonical configuration contract passed to a provider's initialize().  
  
Concrete providers may ignore fields they don't need; the shape stays  
identical across all providers so the Core Engine never has to special-case  
a provider's config format.  
"""  
  
from dataclasses import dataclass, field  
from typing import Any, Optional  
  
  
@dataclass(frozen=True)  
class ProviderConfig:  
    """  
    Attributes:  
        api_key: Secret credential. Sourced from env / secret manager —  
                 never hardcoded, never logged.  
        model:   Model identifier (e.g. "gpt-4o", "gemini-1.5-pro").  
        extra:   Provider-specific overrides that do not fit the common shape.  
    """  
  
    api_key: Optional[str] = None  
    model: Optional[str] = None  
    extra: dict[str, Any] = field(default_factory=dict)  