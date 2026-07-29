"""
provider_manager.py

Thin coordination layer between the Application / Core Engine and the
Provider Layer.

Design goal (MAFS Chapter 3 + Chapter 9)
----------------------------------------
ProviderManager must remain a *traffic controller*, never the brain of
the Provider Layer.

Single responsibility
---------------------
Orchestrate calls between the Application Layer and already-registered
providers.  Nothing more.

Explicitly outside this class (future tasks will live in their own
components):
    - Provider selection / routing decisions
    - Fallback / retry / circuit-breaker policies
    - Provider lifecycle (initialize, reuse, close)
    - Health-check implementation details
    - Any generation, streaming or tool-calling logic

Lifecycle of a request through this class
-----------------------------------------
1. Application asks Manager for a named provider (or asks it to forward
   a generate call).
2. Manager asks Registry for the provider instance.
3. Manager forwards the call and returns the result.
4. Manager never decides *which* provider should be used and never
   mutates provider state.
"""

from __future__ import annotations

from typing import Any

from providers.base_provider import BaseProvider
from providers.models import ProviderRequest, ProviderResponse
from providers.registry import ProviderRegistry


class ProviderManager:
    """
    Coordinates registered providers for the Core Engine.

    Current responsibilities (Sprint 3 Task 1 — deliberately minimal):
        - Hold a reference to a ProviderRegistry.
        - Expose pure lookup of a named provider.
        - Optionally forward a generate() call (thin delegation only).

    Future extension points are left as comments so that selection and
    fallback logic are added as separate collaborators, not as methods
    that bloat this class into a God Object.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        """
        Args:
            registry: The ProviderRegistry used to look up providers by name.
                      Manager never owns registration or lifecycle logic.
        """
        self._registry = registry

    def get_provider(self, name: str) -> BaseProvider:
        """
        Retrieve a registered provider by name.

        Pure delegation to the registry.  No caching, no initialization,
        no health checks.

        Args:
            name: Registered provider name (e.g. "openai", "gemini").

        Returns:
            BaseProvider: The requested provider instance.

        Raises:
            Whatever the registry raises when the name is unknown.
        """
        return self._registry.get(name)

    def generate(
        self,
        name: str,
        request: ProviderRequest,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Forward a generation request to a named provider.

        This method exists only as a convenience for the Application Layer.
        It performs exactly three steps and nothing else:

            1. Ask the registry for the provider.
            2. Call provider.generate(...).
            3. Return the response.

        No selection, no fallback, no retry, no lifecycle management.

        Args:
            name:    Registered provider name.
            request: Canonical ProviderRequest.
            **kwargs: Optional provider-specific extras.

        Returns:
            ProviderResponse produced by the concrete provider.
        """
        provider = self.get_provider(name)
        return provider.generate(request, **kwargs)

    # ------------------------------------------------------------------
    # Future collaborators (do NOT implement inside this class)
    # ------------------------------------------------------------------
    #
    # Provider selection will become its own component, e.g.:
    #   selector: ProviderSelector
    #   def select_and_generate(self, criteria, request) -> ProviderResponse:
    #       name = self._selector.select(criteria)
    #       return self.generate(name, request)
    #
    # Fallback / retry will become its own component, e.g.:
    #   fallback_policy: FallbackPolicy
    #   def generate_with_policy(self, ...) -> ProviderResponse: ...
    #
    # Keeping these concerns outside ProviderManager preserves SRP and
    # prevents the class from growing into a God Object.
