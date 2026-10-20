"""
providers/groq_provider.py

Compatibility module exposing GroqProvider and Groq SDK bindings.
"""
from __future__ import annotations

import sys
from groq import Groq, GroqError as GroqSDKError
from providers.groq.provider import GroqProvider
import providers.groq.provider as _groq_provider_module

# If tests patch providers.groq_provider.Groq, propagate to providers.groq.provider.Groq
class _GroqProviderModule(sys.modules[__name__].__class__):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name == "Groq":
            _groq_provider_module.Groq = value

sys.modules[__name__].__class__ = _GroqProviderModule

__all__ = ["GroqProvider", "Groq", "GroqSDKError"]

