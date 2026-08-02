"""
registry.py

Provider registry for the Provider Layer.

The registry is responsible for maintaining a catalog of registered
providers and efficient lookup indexes.

Responsibilities
----------------
- Register providers
- Unregister providers
- Retrieve provider metadata
- Retrieve provider runtime objects
- List registered providers
- Capability lookup
- Model lookup
- Capability support checks

Explicitly out of scope
-----------------------
- Provider selection
- Routing
- Retry / fallback
- Load balancing
- Health checking
- Provider initialization
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set

from providers.base_provider import BaseProvider
from providers.models.provider_capability import Capability
from providers.models.provider_info import ProviderInfo


class ProviderRegistry:
    """Registry that stores provider metadata and lookup indexes."""

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderInfo] = {}
        self._capability_index: Dict[Capability, Set[str]] = defaultdict(set)
        self._model_index: Dict[str, Set[str]] = defaultdict(set)

    def register(self, info: ProviderInfo) -> None:
        """
        Register a provider.

        Raises:
            ValueError:
                If a provider with the same name already exists.
        """
        if info.name in self._providers:
            raise ValueError(f"Provider '{info.name}' is already registered.")

        self._providers[info.name] = info
        self._add_to_indexes(info)

    def unregister(self, name: str) -> None:
        """
        Remove a provider from the registry.

        Raises:
            KeyError:
                If the provider does not exist.
        """
        info = self._providers.pop(name)
        self._remove_from_indexes(info)

    def clear(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()
        self._capability_index.clear()
        self._model_index.clear()

    def get(self, name: str) -> ProviderInfo:
        """
        Return ProviderInfo for a provider.

        Raises:
            KeyError:
                If the provider is not registered.
        """
        return self._providers[name]

    def get_provider(self, name: str) -> BaseProvider:
        """
        Return the runtime provider instance.

        Raises:
            KeyError:
                If the provider is not registered.
        """
        return self.get(name).provider

    def is_registered(self, name: str) -> bool:
        """Return True if the provider is registered."""
        return name in self._providers

    def list_providers(self) -> List[str]:
        """Return registered provider names."""
        return sorted(self._providers.keys())

    def list_info(self) -> List[ProviderInfo]:
        """Return ProviderInfo objects."""
        return sorted(
            self._providers.values(),
            key=lambda info: info.name,
        )

    def providers_for_capability(
        self,
        capability: Capability,
    ) -> List[ProviderInfo]:
        """Return providers supporting a capability."""
        names = self._capability_index.get(capability, set())
        return sorted(
            (self._providers[name] for name in names),
            key=lambda info: info.name,
        )

    def providers_for_model(self, model: str) -> List[ProviderInfo]:
        """Return providers supporting a model."""
        names = self._model_index.get(model, set())
        return sorted(
            (self._providers[name] for name in names),
            key=lambda info: info.name,
        )

    def supports(self, provider_name: str, capability: Capability) -> bool:
        """
        Return whether a provider supports a capability.

        Raises:
            KeyError:
                If the provider is not registered.
        """
        return self.get(provider_name).capabilities.supports(capability)

    def __contains__(self, name: object) -> bool:
        """Return True if a provider is registered."""
        return isinstance(name, str) and name in self._providers

    def __len__(self) -> int:
        """Return number of registered providers."""
        return len(self._providers)

    def _add_to_indexes(self, info: ProviderInfo) -> None:
        """Populate capability and model indexes."""
        for capability in info.capabilities.supported:
            self._capability_index[capability].add(info.name)

        for model in info.supported_models:
            self._model_index[model].add(info.name)

    def _remove_from_indexes(self, info: ProviderInfo) -> None:
        """Remove provider from capability and model indexes."""
        for capability in info.capabilities.supported:
            providers = self._capability_index.get(capability)
            if providers is None:
                continue

            providers.discard(info.name)

            if not providers:
                del self._capability_index[capability]

        for model in info.supported_models:
            providers = self._model_index.get(model)
            if providers is None:
                continue

            providers.discard(info.name)

            if not providers:
                del self._model_index[model]
