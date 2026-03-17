"""Tests for Mailchk configuration management."""

import os
import pytest
from unittest.mock import patch, MagicMock

from mailchk.config import (
    from_environment,
    configure,
    get_client,
    ConfigurationBuilder,
    create_client_from_env,
)
from mailchk.exceptions import AuthenticationError
from mailchk import Mailchk, AsyncMailchk


class TestFromEnvironment:
    """Tests for from_environment function."""

    def test_from_environment_basic(self, set_env_vars):
        """Test loading basic configuration from environment."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        config = from_environment()

        assert config["api_key"] == "test-api-key"
        assert "base_url" not in config
        assert "timeout" not in config

    def test_from_environment_full_config(self, set_env_vars):
        """Test loading full configuration from environment."""
        set_env_vars(
            MAILCHK_API_KEY="test-api-key",
            MAILCHK_BASE_URL="https://custom-api.com/v1",
            MAILCHK_TIMEOUT="60",
        )

        config = from_environment()

        assert config["api_key"] == "test-api-key"
        assert config["base_url"] == "https://custom-api.com/v1"
        assert config["timeout"] == 60

    def test_from_environment_custom_env_names(self, set_env_vars):
        """Test loading configuration with custom environment variable names."""
        set_env_vars(
            CUSTOM_API_KEY="test-api-key",
            CUSTOM_BASE_URL="https://custom-api.com/v1",
            CUSTOM_TIMEOUT="45",
        )

        config = from_environment(
            api_key_env="CUSTOM_API_KEY",
            base_url_env="CUSTOM_BASE_URL",
            timeout_env="CUSTOM_TIMEOUT",
        )

        assert config["api_key"] == "test-api-key"
        assert config["base_url"] == "https://custom-api.com/v1"
        assert config["timeout"] == 45

    def test_from_environment_with_overrides(self, set_env_vars):
        """Test loading configuration with additional overrides."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        config = from_environment(
            retry_attempts=5,
            retry_delay=2.0,
            custom_option="custom_value",
        )

        assert config["api_key"] == "test-api-key"
        assert config["retry_attempts"] == 5
        assert config["retry_delay"] == 2.0
        assert config["custom_option"] == "custom_value"

    def test_from_environment_missing_api_key(self):
        """Test that missing API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            from_environment()

        assert "MAILCHK_API_KEY" in str(exc_info.value)

    def test_from_environment_invalid_timeout(self, set_env_vars):
        """Test that invalid timeout is ignored."""
        set_env_vars(
            MAILCHK_API_KEY="test-api-key",
            MAILCHK_TIMEOUT="not-a-number",
        )

        config = from_environment()

        assert config["api_key"] == "test-api-key"
        assert "timeout" not in config  # Invalid timeout should be ignored

    @patch("mailchk.config.load_dotenv")
    def test_from_environment_with_env_file(self, mock_load_dotenv, set_env_vars):
        """Test loading environment from .env file."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        config = from_environment(env_file=".env.test")

        mock_load_dotenv.assert_called_once_with(".env.test")
        assert config["api_key"] == "test-api-key"

    @patch("mailchk.config.load_dotenv")
    def test_from_environment_default_env_file(self, mock_load_dotenv, set_env_vars):
        """Test loading environment without specifying .env file."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        config = from_environment()

        mock_load_dotenv.assert_called_once_with()
        assert config["api_key"] == "test-api-key"


class TestConfigure:
    """Tests for configure function."""

    def test_configure_with_api_key(self):
        """Test configuring with explicit API key."""
        configure(api_key="test-api-key", timeout=30)

        client = get_client()
        assert isinstance(client, Mailchk)

        async_client = get_client(async_client=True)
        assert isinstance(async_client, AsyncMailchk)

    def test_configure_from_environment(self, set_env_vars):
        """Test configuring from environment variables."""
        set_env_vars(
            MAILCHK_API_KEY="env-api-key",
            MAILCHK_TIMEOUT="45",
        )

        configure()

        client = get_client()
        assert isinstance(client, Mailchk)
        assert client.api_key == "env-api-key"
        assert client.timeout == 45

    def test_configure_with_additional_options(self):
        """Test configuring with additional client options."""
        configure(
            api_key="test-api-key",
            base_url="https://custom-api.com/v1",
            retry_attempts=5,
        )

        client = get_client()
        assert client.api_key == "test-api-key"
        assert client.base_url == "https://custom-api.com/v1"
        assert client.retry_attempts == 5

    @patch("mailchk.config.load_dotenv")
    def test_configure_with_env_file(self, mock_load_dotenv, set_env_vars):
        """Test configuring with custom .env file."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        configure(env_file=".env.production")

        mock_load_dotenv.assert_called_once_with(".env.production")


class TestGetClient:
    """Tests for get_client function."""

    def test_get_client_not_configured(self):
        """Test getting client when not configured raises error."""
        with pytest.raises(RuntimeError) as exc_info:
            get_client()

        assert "No client configured" in str(exc_info.value)

    def test_get_async_client_not_configured(self):
        """Test getting async client when not configured raises error."""
        with pytest.raises(RuntimeError) as exc_info:
            get_client(async_client=True)

        assert "No async client configured" in str(exc_info.value)

    def test_get_client_after_configure(self):
        """Test getting client after configuring."""
        configure(api_key="test-api-key")

        client = get_client()
        assert isinstance(client, Mailchk)
        assert client.api_key == "test-api-key"

        async_client = get_client(async_client=True)
        assert isinstance(async_client, AsyncMailchk)
        assert async_client.api_key == "test-api-key"

    def test_get_client_returns_same_instance(self):
        """Test that get_client returns the same instance."""
        configure(api_key="test-api-key")

        client1 = get_client()
        client2 = get_client()
        assert client1 is client2

        async_client1 = get_client(async_client=True)
        async_client2 = get_client(async_client=True)
        assert async_client1 is async_client2


class TestConfigurationBuilder:
    """Tests for ConfigurationBuilder class."""

    def test_builder_basic(self):
        """Test basic builder pattern usage."""
        config = (
            ConfigurationBuilder()
            .api_key("test-api-key")
            .base_url("https://custom-api.com")
            .timeout(60)
            .build()
        )

        assert config["api_key"] == "test-api-key"
        assert config["base_url"] == "https://custom-api.com"
        assert config["timeout"] == 60

    def test_builder_method_chaining(self):
        """Test that builder methods return self for chaining."""
        builder = ConfigurationBuilder()

        result = builder.api_key("test-api-key")
        assert result is builder

        result = builder.base_url("https://test.com")
        assert result is builder

        result = builder.timeout(30)
        assert result is builder

    def test_builder_missing_api_key(self):
        """Test that building without API key raises error."""
        builder = ConfigurationBuilder().timeout(30)

        with pytest.raises(AuthenticationError):
            builder.build()

    def test_builder_from_env(self, set_env_vars):
        """Test builder loading from environment."""
        set_env_vars(
            MAILCHK_API_KEY="env-api-key",
            MAILCHK_BASE_URL="https://env-api.com",
        )

        config = ConfigurationBuilder().from_env().timeout(45).build()

        assert config["api_key"] == "env-api-key"
        assert config["base_url"] == "https://env-api.com"
        assert config["timeout"] == 45

    def test_builder_from_env_with_custom_mappings(self, set_env_vars):
        """Test builder with custom environment variable mappings."""
        set_env_vars(CUSTOM_API_KEY="test-api-key")

        config = (
            ConfigurationBuilder()
            .from_env(api_key_env="CUSTOM_API_KEY")
            .build()
        )

        assert config["api_key"] == "test-api-key"

    @patch("mailchk.config.load_dotenv")
    def test_builder_from_env_with_file(self, mock_load_dotenv, set_env_vars):
        """Test builder loading from custom .env file."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        config = (
            ConfigurationBuilder()
            .from_env(env_file=".env.test")
            .build()
        )

        mock_load_dotenv.assert_called_once_with(".env.test")
        assert config["api_key"] == "test-api-key"

    def test_builder_override_env_values(self, set_env_vars):
        """Test that builder methods can override environment values."""
        set_env_vars(
            MAILCHK_API_KEY="env-api-key",
            MAILCHK_TIMEOUT="60",
        )

        config = (
            ConfigurationBuilder()
            .from_env()
            .api_key("override-api-key")  # Override env value
            .timeout(30)  # Override env value
            .build()
        )

        assert config["api_key"] == "override-api-key"
        assert config["timeout"] == 30


class TestCreateClientFromEnv:
    """Tests for create_client_from_env function."""

    def test_create_sync_client_from_env(self, set_env_vars):
        """Test creating sync client from environment."""
        set_env_vars(
            MAILCHK_API_KEY="test-api-key",
            MAILCHK_BASE_URL="https://custom-api.com",
        )

        client = create_client_from_env()

        assert isinstance(client, Mailchk)
        assert client.api_key == "test-api-key"
        assert client.base_url == "https://custom-api.com"

    def test_create_async_client_from_env(self, set_env_vars):
        """Test creating async client from environment."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        client = create_client_from_env(async_client=True)

        assert isinstance(client, AsyncMailchk)
        assert client.api_key == "test-api-key"

    def test_create_client_from_env_missing_api_key(self):
        """Test creating client with missing API key raises error."""
        with pytest.raises(AuthenticationError):
            create_client_from_env()

    @patch("mailchk.config.load_dotenv")
    def test_create_client_from_custom_env_file(self, mock_load_dotenv, set_env_vars):
        """Test creating client from custom .env file."""
        set_env_vars(MAILCHK_API_KEY="test-api-key")

        client = create_client_from_env(env_file=".env.production")

        mock_load_dotenv.assert_called_once_with(".env.production")
        assert isinstance(client, Mailchk)


class TestGlobalStateManagement:
    """Tests for global state management in configuration."""

    def test_configure_resets_global_clients(self):
        """Test that configure() resets global client instances."""
        # Configure with first API key
        configure(api_key="first-key")
        client1 = get_client()

        # Configure with second API key
        configure(api_key="second-key")
        client2 = get_client()

        # Should be different instances with different API keys
        assert client1 is not client2
        assert client1.api_key == "first-key"
        assert client2.api_key == "second-key"

    def test_multiple_configure_calls(self):
        """Test that multiple configure calls work correctly."""
        # First configuration
        configure(api_key="key1", timeout=30)
        client1 = get_client()
        assert client1.api_key == "key1"
        assert client1.timeout == 30

        # Second configuration
        configure(api_key="key2", timeout=60)
        client2 = get_client()
        assert client2.api_key == "key2"
        assert client2.timeout == 60

        # Should be different instances
        assert client1 is not client2