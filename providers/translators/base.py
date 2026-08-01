"""
providers/translators/base.py

Abstract contract for SDK-exception → framework-exception translators.
Sprint 3 Task 5 (AR1 Redesign) — Phase 4 (Translator Layer).

Design summary
---------------
BaseExceptionTranslator defines the single method every provider-specific
translator must implement. Translators are pure mapping functions:

    SDK Exception  →  Framework Provider Exception

They perform no I/O, hold no provider state, and never depend on
ProviderManager, Registry, or the Core Engine.

IB-AR alignment:
    - Chapter 7  (Tool Rules): single responsibility — exception mapping.
    - Chapter 9  (Coding Standard): ABC, full type hints, snake_case.
    - Dependency Inversion: providers depend on this abstraction; the
      Core never depends on any concrete SDK exception type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseExceptionTranslator(ABC):
    """
    Contract for converting provider-SDK exceptions into framework-wide
    Provider exceptions.

    Implementations must be stateless and side-effect free. The returned
    exception is always raised by the caller (`raise translator.translate(exc)
    from exc`); translators never raise themselves.
    """

    @abstractmethod
    def translate(self, exception: Exception) -> Exception:
        """
        Map *exception* to the appropriate framework Provider exception.

        Parameters
        ----------
        exception:
            The raw exception caught from the SDK (or any other source).

        Returns
        -------
        Exception
            A framework Provider exception. Callers must ``raise`` the
            returned value (preferably with ``from exception`` to preserve
            the cause chain).
        """
        ...