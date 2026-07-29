"""  
provider_request.py  
  
Canonical request contract sent to generate() / stream().  
  
Keeps the provider interface stable while allowing future features  
(vision, tools, JSON mode, audio, …) to be expressed as optional fields  
or nested objects without touching BaseProvider.  
"""  
  
from dataclasses import dataclass, field  
from typing import Any, Optional  
  
  
@dataclass  
class ProviderRequest:  
    """  
    Attributes:  
        prompt:          Primary text instruction.  
        system:          Optional system / developer message.  
        messages:        Optional chat-history style messages (list of dicts).  
        temperature:     Sampling temperature.  
        max_tokens:      Maximum tokens to generate.  
        tools:           Optional tool / function definitions.  
        tool_choice:     Optional tool-choice directive.  
        response_format: Optional JSON-mode / schema directive.  
        images:          Optional list of image payloads (vision).  
        audio:           Optional audio payload.  
        extra:           Catch-all for provider-specific parameters.  
    """  
  
    prompt: str  
    system: Optional[str] = None  
    messages: Optional[list[dict[str, Any]]] = None  
    temperature: Optional[float] = None  
    max_tokens: Optional[int] = None  
    tools: Optional[list[dict[str, Any]]] = None  
    tool_choice: Optional[Any] = None  
    response_format: Optional[dict[str, Any]] = None  
    images: Optional[list[Any]] = None  
    audio: Optional[Any] = None  
    extra: dict[str, Any] = field(default_factory=dict)  