"""
providers/translators/__init__.py

Public surface of the Translator Layer.

Re-exports the base contract and the OpenAI concrete translator so that
call sites can write:

    from providers.translators import BaseExceptionTranslator
    from providers.translators import OpenAIExceptionTranslator

Future providers (Gemini, Groq, Claude, Grok, Ollama) add their own
translator modules here following the same pattern.
"""

from __future__ import annotations

from providers.translators.base import BaseExceptionTranslator
from providers.translators.openai import OpenAIExceptionTranslator

__all__ = [
    "BaseExceptionTranslator",
    "OpenAIExceptionTranslator",
]