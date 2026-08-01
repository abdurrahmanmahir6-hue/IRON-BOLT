"""
providers/gemini/__init__.py

Public surface of the Gemini provider package.

Re-exports `GeminiProvider` so that
`from providers.gemini import GeminiProvider` works after this package
replaced the old flat `providers/gemini_provider.py` module.

Phase 5 (Package Split): package layout only — no architectural changes.
"""

from __future__ import annotations

from providers.gemini.provider import GeminiProvider

__all__ = ["GeminiProvider"]