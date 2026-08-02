"""  
provider_capability.py  
  
Declares what a concrete provider is able to do.  
Used by the Router / Orchestrator for capability-based routing  
without hard-coding provider names.  
"""  
  
from dataclasses import dataclass, field  
from enum import Enum  
from typing import Set  
  
  
class Capability(str, Enum):  
    TEXT = "text"  
    STREAMING = "streaming"  
    VISION = "vision"  
    AUDIO = "audio"  
    TOOL_CALLING = "tool_calling"  
    JSON_MODE = "json_mode"  
    EMBEDDINGS = "embeddings"  
    REASONING = "reasoning"  
  
  
@dataclass(frozen=True)  
class ProviderCapability:  
    """  
    Attributes:  
        supported: Set of Capability values the provider implements.  
    """  
  
    supported: Set[Capability] = field(default_factory=set)  
  
    def supports(self, capability: Capability) -> bool:  
        return capability in self.supported  
    # Class-level aliases for convenience access (e.g. ProviderCapability.CHAT)
    CHAT = Capability.CHAT
    TEXT = Capability.TEXT
    STREAMING = Capability.STREAMING
    VISION = Capability.VISION
    AUDIO = Capability.AUDIO
    TOOL_CALLING = Capability.TOOL_CALLING
    JSON_MODE = Capability.JSON_MODE
    EMBEDDINGS = Capability.EMBEDDINGS
    REASONING = Capability.REASONING
