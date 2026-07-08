"""
core/config.py
Responsible for:
    - Loading environment variables from .env via python-dotenv.
    - Validating required fields (API keys, log levels, database DSNs, MCP URLs).
    - Providing a single source of truth for all system settings via Singleton.
MAFS (Mahir Agentic Framework Standard) Compliance:
    - Ch.2 (Truth Over Flattery): Fails fast if required keys are missing or invalid.
    - Ch.2 (Security): Masks secrets in __repr__, __str__, and masked_summary().
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Raised when the configuration is invalid or missing required fields."""
    pass

def _parse_bool(val: Any) -> bool:
    """Helper to parse common boolean inputs."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).lower().strip()
    if s in {"true", "1", "yes", "on"}:
        return True
    if s in {"false", "0", "no", "off"}:
        return False
    return False

def _parse_int(val: Any, field_name: str) -> int:
    """Helper to parse integers with clear error messages."""
    try:
        return int(val)
    except (ValueError, TypeError):
        raise ConfigError(f"Invalid integer for {field_name}: {val}")

@dataclass
class Config:
    """
    Application-wide configuration (Singleton).
    Access values via attributes (e.g., config.openai_api_key).
    Use get_config() to retrieve the singleton instance.
    """
    # System Settings
    app_name: str = "Mahir AI OS"
    app_version: str = "AR1"
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # API Keys (Secrets)
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # Database Settings
    db_backend: str = "sqlite"
    postgres_dsn: Optional[str] = None

    # MCP Settings
    mcp_server_urls: List[str] = field(default_factory=list)

    # Memory Settings
    memory_short_term_ttl: int = 3600

    _instance: Optional[Config] = None

    def __post_init__(self):
        # Normalize environment aliases
        env_aliases = {
            "dev": "development",
            "prod": "production",
            "test": "test"
        }
        self.environment = env_aliases.get(self.environment.lower(), self.environment.lower())

    def __repr__(self) -> str:
        """Security: Mask secrets in repr."""
        return f"Config(app_name={self.app_name!r}, environment={self.environment!r}, log_level={self.log_level!r}, secrets_masked=True)"

    def __str__(self) -> str:
        """Security: Mask secrets in str."""
        return self.__repr__()

    @classmethod
    def load(cls, dotenv_path: Optional[str] = None) -> Config:
        """
        Factory method to load config from environment variables.
        Note: For Singleton access, use get_config().
        """
        load_dotenv(dotenv_path=dotenv_path)

        # Parse MCP URLs
        mcp_urls_raw = os.getenv("MCP_SERVER_URLS", "")
        mcp_urls = [u.strip() for u in mcp_urls_raw.split(",") if u.strip()]

        return Config(
            app_name=os.getenv("APP_NAME", "Mahir AI OS"),
            app_version=os.getenv("APP_VERSION", "AR1"),
            environment=os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            debug=_parse_bool(os.getenv("DEBUG", "false")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            db_backend=os.getenv("DB_BACKEND", "sqlite").lower(),
            postgres_dsn=os.getenv("POSTGRES_DSN"),
            mcp_server_urls=mcp_urls,
            memory_short_term_ttl=_parse_int(os.getenv("MEMORY_SHORT_TERM_TTL", "3600"), "MEMORY_SHORT_TERM_TTL")
        )

    def validate(self, strict: bool = False) -> None:
        """
        Ensure the configuration is valid.
        """
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_log_levels:
            raise ConfigError(f"Invalid LOG_LEVEL: {self.log_level}")

        # Environment Validation
        valid_envs = {"development", "production", "test"}
        if self.environment not in valid_envs:
            raise ConfigError(f"Invalid environment: {self.environment}. Must be one of {valid_envs}")

        # Database Validation
        if self.db_backend == "postgresql" and not self.postgres_dsn:
            raise ConfigError("POSTGRES_DSN is required when DB_BACKEND is 'postgresql'")

        # MCP Validation
        for url in self.mcp_server_urls:
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ConfigError(f"Invalid MCP Server URL: {url}. Must start with http:// or https://")

        if strict:
            has_any_key = any([self.openai_api_key, self.gemini_api_key, self.tavily_api_key])
            if not has_any_key:
                raise ConfigError(
                    "No provider API keys found. Set at least one of "
                    "OPENAI_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY in .env."
                )

    def masked_summary(self) -> dict:
        """
        Returns a dictionary of config values with secrets masked.
        """
        def _mask(val: Optional[str]) -> str:
            if not val:
                return "not set"
            if len(val) <= 8:
                return "set (********)"
            return f"set ({val[:4]}...{val[-4:]})"

        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "environment": self.environment,
            "log_level": self.log_level,
            "debug": self.debug,
            "db_backend": self.db_backend,
            "openai_api_key": _mask(self.openai_api_key),
            "gemini_api_key": _mask(self.gemini_api_key),
            "tavily_api_key": _mask(self.tavily_api_key),
            "mcp_server_urls": self.mcp_server_urls,
            "memory_short_term_ttl": self.memory_short_term_ttl
        }

_global_config: Optional[Config] = None

def get_config(dotenv_path: Optional[str] = None) -> Config:
    """Retrieve the global Singleton Config instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config.load(dotenv_path=dotenv_path)
    return _global_config
