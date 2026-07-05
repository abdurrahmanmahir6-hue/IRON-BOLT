"""
core/config.py

Responsible for:
    - Loading configuration from environment variables (.env file).
    - Validating that required settings are present.
    - Exposing configuration safely to the rest of the system.

Design notes:
    - This module is intentionally provider-agnostic. It does NOT
      hardcode any specific AI provider's model name or endpoint.
      Provider-specific configuration will be added in Sprint 4
      (Provider Layer) without requiring changes to this file's
      public interface.
    - Uses a plain dataclass instead of a framework-specific settings
      object so Sprint 2 introduces zero new hard dependencies beyond
      python-dotenv (which itself degrades gracefully if not
      installed). This can be swapped for `pydantic.BaseSettings`
      later without breaking call sites, since callers only depend on
      attribute access (config.openai_api_key, etc.), not on the
      underlying implementation.
    - Per MAFS Ch.10 (Security): no API key is ever hardcoded here.
      Keys are read from the environment only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover - environment without the package
    _DOTENV_AVAILABLE = False


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """
    Immutable application configuration.

    Attributes:
        app_name: Human-readable name of the application.
        app_version: Current version string (e.g. "AR1").
        environment: Deployment environment ("development", "production").
        log_level: Minimum log level for the logger ("DEBUG", "INFO", ...).
        openai_api_key: API key for OpenAI, if configured.
        gemini_api_key: API key for Google Gemini, if configured.
        tavily_api_key: API key for Tavily search, if configured.

    Note:
        No AI provider calls happen in Sprint 2. Keys are only loaded
        and optionally validated for *presence*, so Sprint 4's
        Provider Layer can consume them without touching this file.
    """

    app_name: str = "Mahir AI OS"
    app_version: str = "AR1"
    environment: str = "development"
    log_level: str = "INFO"

    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    @staticmethod
    def load(dotenv_path: Optional[str] = None) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            dotenv_path: Optional explicit path to a .env file. If None,
                the default `.env` in the current working directory is
                used when python-dotenv is installed.

        Returns:
            A populated, immutable Config instance.
        """
        if _DOTENV_AVAILABLE:
            load_dotenv(dotenv_path=dotenv_path)

        return Config(
            app_name=os.getenv("APP_NAME", "Mahir AI OS"),
            app_version=os.getenv("APP_VERSION", "AR1"),
            environment=os.getenv("ENVIRONMENT", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
        )

    def validate(self, strict: bool = False) -> None:
        """
        Validate configuration.

        Args:
            strict: If True, raise ConfigError when no provider API key
                is set at all. Sprint 2 never calls a provider, so this
                defaults to False. Sprint 4+ should call
                `config.validate(strict=True)` before making live calls.

        Raises:
            ConfigError: If strict validation fails.
        """
        if strict:
            has_any_key = any(
                [self.openai_api_key, self.gemini_api_key, self.tavily_api_key]
            )
            if not has_any_key:
                raise ConfigError(
                    "No provider API keys found. Set at least one of "
                    "OPENAI_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY in .env."
                )

    def masked_summary(self) -> dict:
        """
        Return a dict summary of this config with secrets masked.

        Lets other modules (e.g. logger) report config state at
        startup without ever leaking key material into logs.
        """

        def _mask(value: Optional[str]) -> str:
            return f"set ({len(value)} chars)" if value else "not set"

        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "environment": self.environment,
            "log_level": self.log_level,
            "openai_api_key": _mask(self.openai_api_key),
            "gemini_api_key": _mask(self.gemini_api_key),
            "tavily_api_key": _mask(self.tavily_api_key),
        }
