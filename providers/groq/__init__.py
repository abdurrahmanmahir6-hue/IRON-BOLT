"""
providers/groq/__init__.py

Public surface of the Groq provider package.

Re-exports the provider class and the static metadata symbols that
registry, routing, and documentation layers consume without
instantiating the provider. Mirrors the public surface of the OpenAI
and Gemini packages.

Architecture note
-----------------
Business logic lives in provider.py / mapper.py. This module is a pure
re-export surface.
"""

from __future__ import annotations

from providers.groq.capability import GROQ_CAPABILITIES
from providers.groq.constants import (
    DEFAULT_MODEL,
    DISPLAY_NAME,
    PROVIDER_NAME,
)
from providers.groq.provider import GroqProvider

__all__ = [
    "GroqProvider",
    "GROQ_CAPABILITIES",
    "PROVIDER_NAME",
    "DISPLAY_NAME",
    "DEFAULT_MODEL",
]