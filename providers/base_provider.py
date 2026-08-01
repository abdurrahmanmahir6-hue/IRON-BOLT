"""  
base_provider.py  
  
Defines the abstract contract that every AI provider must implement.  
  
This module contains NO data models and NO implementation logic.  
It exists purely so the Core Engine (Orchestrator / Router) can depend  
on this abstraction instead of any concrete provider.  
  
Design principles  
-----------------  
- Dependency Inversion Principle (DIP)  
- Single Responsibility Principle (SRP) — this file is ONLY the contract  
- Open/Closed — new features are added via Request/Response/Capability  
  models, not by changing this file  
  
Lifecycle  
---------  
1. initialize()   — set up client/session from ProviderConfig  
2. generate()     — single-shot generation  
3. health_check() — reachability / usability probe  
4. close()        — release resources  
"""  
  
from abc import ABC, abstractmethod  
from typing import Any  
  
from providers.models import ProviderConfig, ProviderRequest, ProviderResponse, ProviderInfo  
  
  
class BaseProvider(ABC):  
    """  
    Abstract base class. Concrete providers (OpenAIProvider, GeminiProvider, …)  
    implement these four methods and nothing else is required by the Core Engine.  
    """  
  
    @abstractmethod  
    def initialize(self, config: ProviderConfig) -> None:  
        """  
        Prepare the provider (construct SDK client, validate credentials, …).  
        """  
        raise NotImplementedError  
  
    @abstractmethod  
    def generate(self, request: ProviderRequest, **kwargs: Any) -> ProviderResponse:  
        """  
        Perform a single generation call.  
  
        The request object carries all common parameters; provider-specific  
        extras may still be passed via **kwargs or request.extra.  
        """  
        raise NotImplementedError  
  
    @abstractmethod  
    def health_check(self) -> bool:  
        """  
        Return True if the provider is currently reachable and usable.  
        """  
        raise NotImplementedError  
  
    @abstractmethod  
    def close(self) -> None:  
        """  
        Release any held resources (HTTP sessions, connections, …).  
        """  
        raise NotImplementedError  
  
    # Optional but recommended — lets the Router discover capabilities  
    # without hard-coding provider names.  
    @property  
    @abstractmethod  
    def info(self) -> ProviderInfo:  
        """  
        Static metadata + capability set for this provider instance.  
        """  
        raise NotImplementedError  
