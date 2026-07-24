"""
core/config.py
================================================================================
Config লোড হয় শুধু এই ফাইল থেকে। os.getenv() অন্য কোথাও কল করবে না —
সবাই get_config() (বা `config`) ইমপোর্ট করে ভ্যালু নিবে। এই একটা রুল মানলে
সিক্রেট লিক অডিট করা সহজ: os.getenv এর জন্য গ্রেপ করো, এই ফাইল বাদে আর
কোথাও পেলে বুঝবা কেউ রুল ভেঙেছে।

দুই লেয়ারে ভাগ করা আছে:
  - dataclass গুলো শুধু ভ্যালু রাখে (frozen, picklable, simple)
  - loader startup-এ একবার env/.env পড়ে, eager validate করে, dataclass
    বানিয়ে দেয়, তারপর নিজে বাদ পড়ে যায়

এভাবে করার কারণ — Sprint 2 এর পুরনো কলসাইট (Config.load/validate/
masked_summary) ভাঙেনি, আর Sprint 3-এর singleton + subsection dataclass
উপরে বসিয়ে দেওয়া গেছে। পরে কেউ নতুন field যোগ করলে শুধু নিজের subsection
dataclass টাচ করবে, বাকি কিছু না।

Dependency: python-dotenv (hard dependency, না থাকলে gracefully skip করে)
Future: pydantic-settings যোগ হলেও public API (Config, get_config,
ConfigError, masked_summary, validate) অপরিবর্তিত থাকবে — কোথায় বসবে সেটা
নিচে কমেন্টে মার্ক করা আছে।

Security — এগুলো নিয়ে কোনো ছাড় নাই:
  - কোনো secret hardcode না
  - repr()/str()/log/exception — কোথাও secret ভ্যালু আসবে না
  - নতুন secret field হলে SecretValue দিয়ে wrap করবা,
    .get_secret_value() ছাড়া বের করার কোনো রাস্তা নাই
  - ConfigError শুধু key-এর নাম বলবে, ভ্যালু কখনো না

IB-AR রেফারেন্স:
  Ch. 2  — Security by Default (fail-fast validation)
  Ch. 6  — Memory Rules (credential কখনো memory store-এ যাবে না)
  Ch. 10 — Security (env-only secrets, সবখানে masked)

Backward compatibility (Sprint 2 থেকে অক্ষত):
  Config.load(dotenv_path=None) -> Config
  Config.validate(strict=False) -> None
  Config.masked_summary() -> dict
  ConfigError
  config.openai_api_key / gemini_api_key / tavily_api_key
  config.app_name / app_version / ...

Sprint 3-এ যা নতুন যোগ হয়েছে:
  get_config() -> Config                 singleton
  Config.providers / .database / .memory / .mcp / .plugins
  Config.summary()                       masked_summary()-এর alias
  Environment / LogLevel / DatabaseBackend   enums

Sprint 3, Task 3 — environment validation fields:
  Config.providers.active_provider   str
  Config.providers.model             str
  Config.providers.timeout_seconds   float
  Config.providers.temperature       float

নোট: এই চারটা শুধু raw read + type coerce, কোনো ডিপ ভ্যালিডেশন এখানে নাই।
active_provider আসলেই রেজিস্টার্ড কিনা, matching API key আছে কিনা — এসব চেক
core/startup_validation.py-তে। কারণ providers/ প্যাকেজ core/config থেকে
কিছু ইমপোর্ট করে না, আর এখানে providers/ টেনে আনলে circular import হয়ে
যেত। startup_validation.py-ই একমাত্র জায়গা যেখানে দুটো নির্ভরতা একসাথে
থাকার অনুমতি আছে।
================================================================================
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional

# ── optional python-dotenv ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv as _load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================ #
#  Enums — closed, validated vocabularies                                      #
#  A typo in .env produces a clear ConfigError at startup, not a silent       #
#  wrong value that surfaces hours later in production.                        #
# ============================================================================ #

class Environment(str, Enum):
    """Deployment environment.  Drives log verbosity and validation strictness."""
    DEVELOPMENT = "development"
    STAGING     = "staging"
    PRODUCTION  = "production"
    TEST        = "test"

    # Allow short aliases so .env can say ENV=dev or ENV=development equally.
    @classmethod
    def _missing_(cls, value: object) -> Optional["Environment"]:
        aliases: Dict[str, "Environment"] = {
            "dev":  cls.DEVELOPMENT,
            "prod": cls.PRODUCTION,
            "stg":  cls.STAGING,
        }
        return aliases.get(str(value).lower())


class LogLevel(str, Enum):
    DEBUG    = "DEBUG"
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseBackend(str, Enum):
    SQLITE     = "sqlite"
    POSTGRESQL = "postgresql"


# ============================================================================ #
#  SecretValue — lightweight secret wrapper                                    #
#                                                                              #
#  Why not pydantic SecretStr?                                                 #
#  pydantic-settings is not a hard dependency in Sprint 2/3. This class       #
#  replicates the security contract (masked repr, explicit accessor) with      #
#  zero extra imports. When pydantic-settings is adopted, replace this class  #
#  with SecretStr and nothing at call sites changes.                           #
# ============================================================================ #

class SecretValue:
    """
    Opaque holder for a secret string.

    repr() and str() always return '**masked**' so the value cannot leak
    into logs, exception messages, or crash reports.

    Usage::

        key = SecretValue("sk-…")
        actual = key.get_secret_value()   # only explicit call exposes the value
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def get_secret_value(self) -> str:
        return object.__getattribute__(self, "_value")

    def __repr__(self) -> str:
        return "SecretValue('**masked**')"

    def __str__(self) -> str:
        return "**masked**"

    def __bool__(self) -> bool:
        return bool(self._value)

    # Prevent accidental attribute writes
    def __setattr__(self, name: str, value: object) -> None:  # type: ignore[override]
        raise AttributeError("SecretValue is immutable")


# ============================================================================ #
#  ConfigError                                                                 #
# ============================================================================ #

class ConfigError(ValueError):
    """
    Raised when required configuration is missing or invalid.

    Inherits from ValueError so it can be caught alongside pydantic's
    ValidationError in a single ``except (ConfigError, ValueError)`` block —
    useful when migrating to pydantic-settings later.
    """


# ============================================================================ #
#  Subsection dataclasses                                                      #
#  Each group is frozen so it cannot be mutated after construction.            #
#  Each group is independently testable by constructing it directly.          #
# ============================================================================ #

@dataclass(frozen=True)
class ProviderConfig:
    """
    LLM and search-provider credentials, plus the active provider's runtime
    parameters (Sprint 3 Task 3).

    All *_api_key fields are Optional[SecretValue]; None means the key was
    not set. Callers check `if config.providers.openai_api_key` before use.

    To add a new provider (Claude, Grok, DeepSeek, Ollama, OpenRouter):
    1. Add one field here.
    2. Add its name to _PROVIDER_FIELD_NAMES below.
    3. Set the matching env var. No other file changes required.

    Backward compat: .openai_api_key etc. exist as *properties* on Config
    itself (see Config class below) so Sprint 2 call sites continue to work.

    Sprint 3 Task 3 additions
    -------------------------
    active_provider / model / timeout_seconds / temperature are plain,
    permissively-parsed values. This dataclass does NOT judge whether
    active_provider names a *known* provider, whether model is realistic, or
    whether timeout/temperature are in a sane range — that cross-cutting
    judgment belongs to core/startup_validation.py, which runs explicitly at
    startup and can also cross-check against the provider registry. Keeping
    this dataclass permissive avoids duplicating validation logic in two
    places and keeps this file's diff minimal.
    """

    openai_api_key:     Optional[SecretValue] = None
    gemini_api_key:     Optional[SecretValue] = None
    tavily_api_key:     Optional[SecretValue] = None
    claude_api_key:     Optional[SecretValue] = None
    grok_api_key:       Optional[SecretValue] = None
    deepseek_api_key:   Optional[SecretValue] = None
    openrouter_api_key: Optional[SecretValue] = None
    groq_api_key:       Optional[SecretValue] = None
    ollama_base_url:    str = "http://localhost:11434"

    # ── Sprint 3 Task 3: active provider runtime parameters ────────────────
    active_provider: str   = "groq"
    model:           str   = "openai/gpt-oss-120b"
    timeout_seconds: float = 30.0
    temperature:     float = 0.7

    def get_key(self, provider: str) -> Optional[str]:
        """
        Return the raw secret string for *provider*, or None if unset.

        Example::

            raw_key = config.providers.get_key("openai")
        """
        secret: Optional[SecretValue] = getattr(
            self, f"{provider.lower()}_api_key", None
        )
        return secret.get_secret_value() if secret else None

    def configured_providers(self) -> List[str]:
        """Names of providers that currently have a key set (safe to log)."""
        return [
            name for name in _PROVIDER_FIELD_NAMES if self.get_key(name)
        ]


# Provider names that map to fields of the form ``{name}_api_key``.
_PROVIDER_FIELD_NAMES: List[str] = [
    "openai", "gemini", "tavily", "claude", "grok", "deepseek", "openrouter", "groq"
]


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Database backend selection and connection parameters.

    SQLite is the default and requires no extra configuration.
    PostgreSQL requires POSTGRES_DSN to be set; construction fails otherwise.
    """

    backend:     DatabaseBackend       = DatabaseBackend.SQLITE
    sqlite_path: str                   = "./database/mahir.db"
    postgres_dsn: Optional[SecretValue] = None

    def __post_init__(self) -> None:
        if (
            self.backend == DatabaseBackend.POSTGRESQL
            and not self.postgres_dsn
        ):
            raise ConfigError(
                "DB_BACKEND=postgresql requires POSTGRES_DSN to be set in .env."
            )


@dataclass(frozen=True)
class MemoryConfig:
    """
    Memory Manager parameters (MAFS Chapter 6).

    Credentials are never stored here — they live in ProviderConfig.
    """

    short_term_ttl_seconds: int  = 3600
    long_term_enabled:      bool = False
    retention_days:         int  = 30


@dataclass(frozen=True)
class MCPConfig:
    """
    Model Context Protocol integration settings.

    server_urls is parsed from the comma-separated MCP_SERVER_URLS env var
    at construction time so callers always receive a clean list.
    """

    enabled:     bool      = False
    server_urls: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Validate URLs are non-empty strings (not necessarily http; local
        # socket paths are valid MCP transports).
        for url in self.server_urls:
            if not isinstance(url, str) or not url.strip():
                raise ConfigError(
                    f"MCP_SERVER_URLS contains an invalid entry: {url!r}"
                )


@dataclass(frozen=True)
class PluginConfig:
    """Plugin discovery settings."""

    enabled:   bool = False
    directory: str  = "./plugins"


# ============================================================================ #
#  Root Config                                                                 #
#                                                                              #
#  This is the single object the rest of the codebase touches.                #
#  Construct it via get_config() — not directly.                              #
# ============================================================================ #

@dataclass(frozen=True)
class Config:
    """
    Immutable application configuration for Iron Bolt.

    This object is the sole source of truth for runtime configuration.
    It is constructed once (via get_config / Config.load) and cached for
    the process lifetime.

    Sprint 2 call sites continue to work unchanged::

        config = Config.load()
        config.validate()
        config.masked_summary()
        config.openai_api_key   # → str | None (plain string, not SecretValue)

    Sprint 3+ call sites use subsections::

        config = get_config()
        config.providers.get_key("claude")
        config.database.backend
        config.mcp.server_urls
    """

    # ── core identity ──────────────────────────────────────────────────────
    app_name:    str         = "Iron Bolt"
    app_version: str         = "AR1"
    environment: Environment = Environment.DEVELOPMENT
    log_level:   LogLevel    = LogLevel.INFO
    log_dir:     str         = "./logs"

    # ── subsections ────────────────────────────────────────────────────────
    providers: ProviderConfig  = field(default_factory=ProviderConfig)
    database:  DatabaseConfig  = field(default_factory=DatabaseConfig)
    memory:    MemoryConfig    = field(default_factory=MemoryConfig)
    mcp:       MCPConfig       = field(default_factory=MCPConfig)
    plugins:   PluginConfig    = field(default_factory=PluginConfig)

    # ── Sprint 2 backward-compatibility properties ──────────────────────── #
    # These expose provider keys as plain str | None so existing call sites  #
    # (config.openai_api_key, config.gemini_api_key, etc.) never break.     #
    # The properties unwrap SecretValue transparently.

    @property
    def openai_api_key(self) -> Optional[str]:
        """Sprint 2 compat: plain string (or None) for the OpenAI key."""
        return self.providers.get_key("openai")

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Sprint 2 compat: plain string (or None) for the Gemini key."""
        return self.providers.get_key("gemini")

    @property
    def tavily_api_key(self) -> Optional[str]:
        """Sprint 2 compat: plain string (or None) for the Tavily key."""
        return self.providers.get_key("tavily")

    # ── public API ─────────────────────────────────────────────────────────

    @staticmethod
    def load(dotenv_path: Optional[str] = None) -> "Config":
        """
        Load and return a fully-validated Config from the environment.

        This is the Sprint 2 factory. It is a thin wrapper around _build()
        so that Config.load() and get_config() share identical logic.

        Args:
            dotenv_path: Path to a .env file. Defaults to '.env' in the
                current working directory when python-dotenv is available.

        Returns:
            A frozen, validated Config instance.

        Raises:
            ConfigError: If any required value is missing or invalid.
        """
        return _build(dotenv_path=dotenv_path)

    def validate(self, strict: bool = False) -> None:
        """
        Validate configuration state.

        Sprint 2 signature preserved exactly. Pydantic-style validation
        already happened at construction time (fail-fast). This method
        exists as an explicit hook for callers that want a named call in
        their startup sequence.

        Args:
            strict: When True, raise ConfigError if no provider API key
                is configured and the environment is not TEST. Sprint 2
                defaulted to False; Sprint 4+ should call validate(strict=True)
                before making live provider calls.

        Raises:
            ConfigError: On strict validation failure.
        """
        if strict and self.environment != Environment.TEST:
            if not self.providers.configured_providers():
                raise ConfigError(
                    "strict=True: no provider API key configured. "
                    "Set at least one of GROQ_API_KEY / OPENAI_API_KEY / "
                    "GEMINI_API_KEY / CLAUDE_API_KEY / TAVILY_API_KEY in .env."
                )

    # validate_startup is the Sprint 3 name; alias it so both names work.
    def validate_startup(self, strict: bool = False) -> "Config":
        """Sprint 3 alias for validate(). Returns self for chaining."""
        self.validate(strict=strict)
        return self

    def masked_summary(self) -> dict:
        """
        Sprint 2 contract: return a dict with secrets masked.

        All Sprint 2 keys are present. New Sprint 3 keys are appended so
        existing callers that iterate the dict are not broken.

        Safe to pass directly to logging.info / json.dumps.
        """
        def _mask(secret: Optional[SecretValue]) -> str:
            if not secret:
                return "not set"
            length = len(secret.get_secret_value())
            return f"set ({length} chars)"

        return {
            # Sprint 2 keys — order and names unchanged
            "app_name":        self.app_name,
            "app_version":     self.app_version,
            "environment":     self.environment.value,
            "log_level":       self.log_level.value,
            "openai_api_key":  _mask(self.providers.openai_api_key),
            "gemini_api_key":  _mask(self.providers.gemini_api_key),
            "tavily_api_key":  _mask(self.providers.tavily_api_key),
            # Sprint 3 additions
            "claude_api_key":       _mask(self.providers.claude_api_key),
            "grok_api_key":         _mask(self.providers.grok_api_key),
            "deepseek_api_key":     _mask(self.providers.deepseek_api_key),
            "openrouter_api_key":   _mask(self.providers.openrouter_api_key),
            "groq_api_key":         _mask(self.providers.groq_api_key),
            "database_backend":     self.database.backend.value,
            "configured_providers": self.providers.configured_providers(),
            "mcp_enabled":          self.mcp.enabled,
            "mcp_server_count":     len(self.mcp.server_urls),
            "plugins_enabled":      self.plugins.enabled,
            "memory_long_term":     self.memory.long_term_enabled,
        }

    # Sprint 3 alias — summary() and masked_summary() are identical.
    def summary(self) -> dict:
        """Alias for masked_summary(). Preferred name in Sprint 3+ call sites."""
        return self.masked_summary()


# ============================================================================ #
#  Internal builder — the one place that calls os.getenv                      #
# ============================================================================ #

def _parse_enum(name: str, raw: Optional[str], enum_cls: type, default: object) -> object:
    """
    Parse *raw* as a member of *enum_cls*.

    Raises ConfigError with a human-readable message if the value is not
    recognized. Returns *default* when *raw* is None or empty.
    """
    if not raw:
        return default
    result = enum_cls._missing_(raw.strip()) if hasattr(enum_cls, "_missing_") else None
    # Try normal lookup first (exact match, case-insensitive for str enums).
    try:
        return enum_cls(raw.strip())
    except ValueError:
        pass
    if result is not None:
        return result
    valid = [e.value for e in enum_cls]
    raise ConfigError(
        f"Invalid value for {name}: {raw!r}. "
        f"Must be one of: {', '.join(valid)}"
    )


def _parse_mcp_urls(raw: str) -> List[str]:
    return [u.strip() for u in raw.split(",") if u.strip()]


def _build(dotenv_path: Optional[str] = None) -> Config:
    """
    Read environment variables, validate each field, and return a frozen Config.

    This is the single authorised call site for os.getenv in the module.
    Validation is eager: every field is checked before the Config is returned.
    The first ConfigError is re-raised immediately (fail-fast).
    """
    if _DOTENV_AVAILABLE:
        _load_dotenv(dotenv_path=dotenv_path, override=False)
        # override=False: environment variables already set (e.g. in CI)
        # take precedence over the .env file, which is the expected behaviour.

    def _get(name: str, default: str = "") -> str:
        return os.environ.get(name, default)

    def _secret(name: str) -> Optional[SecretValue]:
        v = os.environ.get(name)
        return SecretValue(v) if v else None

    # ── core ──────────────────────────────────────────────────────────────
    environment: Environment = _parse_enum(  # type: ignore[assignment]
        "ENVIRONMENT / APP_ENV",
        _get("ENVIRONMENT") or _get("APP_ENV"),
        Environment,
        Environment.DEVELOPMENT,
    )
    log_level: LogLevel = _parse_enum(       # type: ignore[assignment]
        "LOG_LEVEL",
        _get("LOG_LEVEL"),
        LogLevel,
        LogLevel.INFO,
    )

    # ── providers ─────────────────────────────────────────────────────────
    def _int(name: str, default: int) -> int:
        raw = _get(name)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"{name} must be an integer, got: {raw!r}")

    def _float(name: str, default: float) -> float:
        """
        Parse *name* as a float. Sprint 3 Task 3 helper — sibling of the
        existing _int/_bool helpers, added for timeout_seconds/temperature.

        Raises:
            ConfigError: If the raw value is set but is not a valid float.
        """
        raw = _get(name)
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            raise ConfigError(f"{name} must be a number, got: {raw!r}")

    providers = ProviderConfig(
        openai_api_key     = _secret("OPENAI_API_KEY"),
        gemini_api_key     = _secret("GEMINI_API_KEY"),
        tavily_api_key     = _secret("TAVILY_API_KEY"),
        claude_api_key     = _secret("CLAUDE_API_KEY"),
        grok_api_key       = _secret("GROK_API_KEY"),
        deepseek_api_key   = _secret("DEEPSEEK_API_KEY"),
        openrouter_api_key = _secret("OPENROUTER_API_KEY"),
        groq_api_key       = _secret("GROQ_API_KEY"),
        ollama_base_url    = _get("OLLAMA_BASE_URL", "http://localhost:11434"),
        # Sprint 3 Task 3 — active provider runtime parameters. Parsed
        # permissively here; core/startup_validation.py judges validity.
        active_provider = _get("ACTIVE_PROVIDER", "groq").strip().lower(),
        model           = _get("MODEL_NAME", "llama-3.1-8b-instant"),
        timeout_seconds = _float("PROVIDER_TIMEOUT_SECONDS", 30.0),
        temperature     = _float("TEMPERATURE", 0.7),
    )

    # ── database ──────────────────────────────────────────────────────────
    db_backend: DatabaseBackend = _parse_enum(  # type: ignore[assignment]
        "DB_BACKEND",
        _get("DB_BACKEND"),
        DatabaseBackend,
        DatabaseBackend.SQLITE,
    )
    database = DatabaseConfig(
        backend      = db_backend,
        sqlite_path  = _get("SQLITE_PATH", "./database/mahir.db"),
        postgres_dsn = _secret("POSTGRES_DSN"),
    )
    # DatabaseConfig.__post_init__ validates PostgreSQL→DSN constraint.

    # ── memory ────────────────────────────────────────────────────────────
    def _bool(name: str, default: bool) -> bool:
        raw = _get(name).lower()
        if not raw:
            return default
        if raw in ("1", "true", "yes", "on"):
            return True
        if raw in ("0", "false", "no", "off"):
            return False
        raise ConfigError(
            f"{name} must be a boolean (true/false/1/0), got: {raw!r}"
        )

    memory = MemoryConfig(
        short_term_ttl_seconds = _int("MEMORY_SHORT_TERM_TTL", 3600),
        long_term_enabled      = _bool("MEMORY_LONG_TERM_ENABLED", False),
        retention_days         = _int("MEMORY_RETENTION_DAYS", 30),
    )

    # ── MCP ───────────────────────────────────────────────────────────────
    mcp_urls_raw = _get("MCP_SERVER_URLS", "")
    mcp = MCPConfig(
        enabled     = _bool("MCP_ENABLED", False),
        server_urls = _parse_mcp_urls(mcp_urls_raw),
    )
    # MCPConfig.__post_init__ validates each URL entry.

    # ── plugins ───────────────────────────────────────────────────────────
    plugins = PluginConfig(
        enabled   = _bool("PLUGINS_ENABLED", False),
        directory = _get("PLUGINS_DIR", "./plugins"),
    )

    return Config(
        app_name    = _get("APP_NAME", "Iron Bolt"),
        app_version = _get("APP_VERSION", "AR1"),
        environment = environment,
        log_level   = log_level,
        log_dir     = _get("LOG_DIR", "./logs"),
        providers   = providers,
        database    = database,
        memory      = memory,
        mcp         = mcp,
        plugins     = plugins,
    )


# ============================================================================ #
#  Process-wide singleton                                                      #
# ============================================================================ #

@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Return the process-wide Config singleton.

    Builds and caches the Config on first call. Subsequent calls return
    the same object with zero overhead (lru_cache with maxsize=1).

    Fails fast: any ConfigError is re-raised immediately so main.py sees
    it at startup — not mid-request.

    Usage::

        from core.config import get_config
        config = get_config()

    Or, for simple one-liner imports::

        from core.config import config

    Testing: call ``get_config.cache_clear()`` before each test that needs
    a fresh configuration derived from a modified environment.
    """
    try:
        return _build()
    except ConfigError:
        raise  # already informative; re-raise as-is
    except Exception as exc:
        # Unexpected errors (MemoryError, PermissionError on .env, etc.)
        print(
            f"[FATAL] Unexpected error building configuration: {exc}",
            file=sys.stderr,
        )
        raise


# Convenience alias — `from core.config import config` for simple call sites.
# Evaluated at import time; a ConfigError here means the process should not
# have started. main.py should wrap `import core.config` in try/except.
#
# NOTE: this line runs _build() once at module import. If this is undesirable
# in test environments, set APP_ENV=test in the test process so validation
# does not require provider keys, then call get_config.cache_clear() as
# needed.
config = get_config()

