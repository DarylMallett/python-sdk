"""Configuration management for Mailchk SDK."""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .client import Mailchk, AsyncMailchk
from .exceptions import AuthenticationError


# Global client instance
_default_client: Optional[Mailchk] = None
_default_async_client: Optional[AsyncMailchk] = None


def from_environment(
    env_file: Optional[str] = None,
    api_key_env: str = "MAILCHK_API_KEY",
    base_url_env: str = "MAILCHK_BASE_URL",
    timeout_env: str = "MAILCHK_TIMEOUT",
    **kwargs
) -> Dict[str, Any]:
    """
    Load Mailchk configuration from environment variables.
    
    Args:
        env_file: Optional path to .env file to load
        api_key_env: Environment variable name for API key
        base_url_env: Environment variable name for base URL
        timeout_env: Environment variable name for timeout
        **kwargs: Additional configuration overrides
        
    Returns:
        Dictionary of configuration values
        
    Raises:
        AuthenticationError: If API key is not found
        
    Example:
        >>> config = from_environment()
        >>> client = Mailchk(**config)
        
        >>> # With custom .env file
        >>> config = from_environment(".env.production")
        >>> client = Mailchk(**config)
    """
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise AuthenticationError(f"Environment variable '{api_key_env}' is required")
    
    config = {
        "api_key": api_key,
        **kwargs
    }
    
    # Optional environment variables
    base_url = os.getenv(base_url_env)
    if base_url:
        config["base_url"] = base_url
    
    timeout = os.getenv(timeout_env)
    if timeout:
        try:
            config["timeout"] = int(timeout)
        except ValueError:
            pass  # Ignore invalid timeout values
    
    return config


def configure(
    api_key: Optional[str] = None,
    env_file: Optional[str] = None,
    **kwargs
) -> None:
    """
    Configure the global default Mailchk client.
    
    Args:
        api_key: API key (if None, will load from environment)
        env_file: Optional path to .env file
        **kwargs: Additional client configuration
        
    Example:
        >>> import mailchk
        >>> mailchk.configure(api_key="your-api-key")
        >>> result = mailchk.get_client().validate("test@example.com")
        
        >>> # From environment
        >>> mailchk.configure()  # Uses MAILCHK_API_KEY from environment
    """
    global _default_client, _default_async_client
    
    if api_key:
        config = {"api_key": api_key, **kwargs}
    else:
        config = from_environment(env_file=env_file, **kwargs)
    
    _default_client = Mailchk(**config)
    _default_async_client = AsyncMailchk(**config)


def get_client(async_client: bool = False) -> Mailchk | AsyncMailchk:
    """
    Get the configured global client instance.
    
    Args:
        async_client: If True, return AsyncMailchk instance
        
    Returns:
        Configured Mailchk or AsyncMailchk instance
        
    Raises:
        RuntimeError: If no client has been configured
        
    Example:
        >>> import mailchk
        >>> mailchk.configure(api_key="your-api-key")
        >>> client = mailchk.get_client()
        >>> result = client.validate("test@example.com")
    """
    if async_client:
        if _default_async_client is None:
            raise RuntimeError(
                "No async client configured. Call configure() first."
            )
        return _default_async_client
    else:
        if _default_client is None:
            raise RuntimeError(
                "No client configured. Call configure() first."
            )
        return _default_client


class ConfigurationBuilder:
    """
    Builder pattern for creating Mailchk client configurations.
    
    Example:
        >>> config = (ConfigurationBuilder()
        ...     .api_key("your-api-key")
        ...     .base_url("https://custom-api.com/v1")
        ...     .timeout(60)
        ...     .build())
        >>> client = Mailchk(**config)
    """
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
    
    def api_key(self, api_key: str) -> "ConfigurationBuilder":
        """Set the API key."""
        self._config["api_key"] = api_key
        return self
    
    def base_url(self, base_url: str) -> "ConfigurationBuilder":
        """Set the base URL."""
        self._config["base_url"] = base_url
        return self
    
    def timeout(self, timeout: int) -> "ConfigurationBuilder":
        """Set the timeout in seconds."""
        self._config["timeout"] = timeout
        return self
    
    def from_env(
        self, 
        env_file: Optional[str] = None,
        **env_mappings
    ) -> "ConfigurationBuilder":
        """Load configuration from environment variables."""
        env_config = from_environment(env_file=env_file, **env_mappings)
        self._config.update(env_config)
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the configuration dictionary."""
        if "api_key" not in self._config:
            raise AuthenticationError("API key is required")
        return self._config.copy()


# Convenience function for creating clients from environment
def create_client_from_env(
    env_file: Optional[str] = None,
    async_client: bool = False
) -> Mailchk | AsyncMailchk:
    """
    Create a client directly from environment variables.
    
    Args:
        env_file: Optional path to .env file
        async_client: If True, return AsyncMailchk instance
        
    Returns:
        Configured Mailchk or AsyncMailchk instance
        
    Example:
        >>> client = create_client_from_env()
        >>> result = client.validate("test@example.com")
    """
    config = from_environment(env_file=env_file)
    
    if async_client:
        return AsyncMailchk(**config)
    else:
        return Mailchk(**config)