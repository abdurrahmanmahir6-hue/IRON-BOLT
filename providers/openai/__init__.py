"""
providers/openai/__init__.py

Public surface of the OpenAI provider package.

Re-exports `OpenAIProvider` (and `OpenAIMapper`) so that
`from providers.openai import OpenAIProvider` keeps working after this
package replaced the old flat `providers/openai_provider.py` module.
Any call site still doing `from providers.openai_provider import
OpenAIProvider` will need updating — that module path no longer exists
after this restructuring.

Phase 3 also re-exports the extracted metadata so registry and
documentation layers can import capabilities / constants without
instantiating the provider.
"""

from __future__ import annotations

from providers.openai.mapper import OpenAIMapper
from providers.openai.provider import OpenAIProvider
from providers.openai.capability import OPENAI_CAPABILITIES
from providers.openai.constants import (
    PROVIDER_NAME,
    DISPLAY_NAME,
    SDK_IDENTIFIER,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_BASE_URL,
)

__all__ = [
    "OpenAIProvider",
    "OpenAIMapper",
    "OPENAI_CAPABILITIES",
    "PROVIDER_NAME",
    "DISPLAY_NAME",
    "SDK_IDENTIFIER",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_BASE_URL",
]