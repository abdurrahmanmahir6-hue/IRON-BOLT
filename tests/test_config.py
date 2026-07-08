"""
tests/test_config.py
Covers core/config.py:
    - Config.load() reads environment variables correctly.
    - Config.load() falls back to sane defaults when env vars are unset.
    - masked_summary() never leaks raw secret values.
    - validate(strict=True) (if applicable) logic verification.
"""
from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from core.config import Config, ConfigError, ProviderConfig, DatabaseConfig, MemoryConfig, MCPConfig, PluginConfig, SecretValue, Environment, LogLevel, DatabaseBackend

# Point at a path that can never exist
_NO_DOTENV_PATH = "/nonexistent/this-file-does-not-exist/.env"

class TestConfigLoad(unittest.TestCase):
    def test_load_uses_defaults_when_env_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load(dotenv_path=_NO_DOTENV_PATH)
            
        self.assertEqual(config.app_name, "Mahir AI OS")
        self.assertEqual(config.app_version, "AR1")
        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertEqual(config.log_level, LogLevel.INFO)
        self.assertIsNone(config.providers.openai_api_key)
        self.assertIsNone(config.providers.gemini_api_key)
        self.assertIsNone(config.providers.tavily_api_key)

    def test_load_reads_environment_variables(self) -> None:
        env = {
            "APP_NAME": "Test OS",
            "APP_VERSION": "AR2",
            "APP_ENV": "production",
            "LOG_LEVEL": "DEBUG",
            "OPENAI_API_KEY": "sk-fake-openai-key",
            "GEMINI_API_KEY": "fake-gemini-key",
            "TAVILY_API_KEY": "fake-tavily-key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.load(dotenv_path=_NO_DOTENV_PATH)
            
        self.assertEqual(config.app_name, "Test OS")
        self.assertEqual(config.app_version, "AR2")
        self.assertEqual(config.environment, Environment.PRODUCTION)
        self.assertEqual(config.log_level, LogLevel.DEBUG)
        self.assertEqual(config.providers.openai_api_key.get_secret_value(), "sk-fake-openai-key")
        self.assertEqual(config.providers.gemini_api_key.get_secret_value(), "fake-gemini-key")
        self.assertEqual(config.providers.tavily_api_key.get_secret_value(), "fake-tavily-key")

class TestConfigMaskedSummary(unittest.TestCase):
    def test_masked_summary_never_leaks_secret_values(self) -> None:
        providers = ProviderConfig(openai_api_key=SecretValue("sk-super-secret-value"))
        config = Config(
            app_name="Test",
            app_version="1.0",
            environment=Environment.TEST,
            log_level=LogLevel.INFO,
            log_dir="./logs",
            providers=providers,
            database=DatabaseConfig(backend=DatabaseBackend.SQLITE),
            memory=MemoryConfig(),
            mcp=MCPConfig(),
            plugins=PluginConfig()
        )
        summary = config.masked_summary()
        summary_str = str(summary)
        self.assertNotIn("sk-super-secret-value", summary_str)
        # In the new config.py, _mask returns "set (X chars)"
        self.assertIn("set (", summary["openai_api_key"])

    def test_masked_summary_reports_not_set(self) -> None:
        providers = ProviderConfig(openai_api_key=None)
        config = Config(
            app_name="Test",
            app_version="1.0",
            environment=Environment.TEST,
            log_level=LogLevel.INFO,
            log_dir="./logs",
            providers=providers,
            database=DatabaseConfig(backend=DatabaseBackend.SQLITE),
            memory=MemoryConfig(),
            mcp=MCPConfig(),
            plugins=PluginConfig()
        )
        self.assertEqual(config.masked_summary()["openai_api_key"], "not set")

class TestConfigValidate(unittest.TestCase):
    def test_strict_passes_with_one_provider_key(self) -> None:
        providers = ProviderConfig(openai_api_key=SecretValue("sk-fake"))
        config = Config(
            app_name="Test",
            app_version="1.0",
            environment=Environment.TEST,
            log_level=LogLevel.INFO,
            log_dir="./logs",
            providers=providers,
            database=DatabaseConfig(backend=DatabaseBackend.SQLITE),
            memory=MemoryConfig(),
            mcp=MCPConfig(),
            plugins=PluginConfig()
        )
        config.validate(strict=True)  # must not raise

    def test_non_strict_never_raises(self) -> None:
        config = Config(
            app_name="Test",
            app_version="1.0",
            environment=Environment.TEST,
            log_level=LogLevel.INFO,
            log_dir="./logs",
            providers=ProviderConfig(),
            database=DatabaseConfig(backend=DatabaseBackend.SQLITE),
            memory=MemoryConfig(),
            mcp=MCPConfig(),
            plugins=PluginConfig()
        )
        config.validate(strict=False)  # must not raise, even with no keys

if __name__ == "__main__":
    unittest.main()
