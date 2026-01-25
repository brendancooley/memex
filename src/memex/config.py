"""Memex configuration management.

Provides layered configuration with precedence:
    1. Environment variables (MEMEX_*)
    2. Config file ($MEMEX_HOME/config.toml)
    3. Defaults defined in MemexConfig
"""

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_memex_home() -> Path:
    """Return the memex home directory.

    Uses MEMEX_HOME environment variable if set, otherwise ~/.memex.
    """
    return Path(os.environ.get("MEMEX_HOME", "~/.memex")).expanduser()


def get_config_path() -> Path:
    """Return the config file path."""
    return get_memex_home() / "config.toml"


class MemexConfig(BaseSettings):
    """Memex configuration with layered precedence.

    Settings are loaded from (highest to lowest priority):
        1. Environment variables with MEMEX_ prefix
        2. Config file at $MEMEX_HOME/config.toml
        3. Default values defined here

    Attributes:
        model: LLM model identifier in 'provider:model-id' format.
    """

    model_config = SettingsConfigDict(
        env_prefix="MEMEX_",
        extra="ignore",
    )

    model: str = "anthropic:claude-sonnet-4-20250514"

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        """Validate model string format without enumerating all models.

        Format must be 'provider:model-id' (e.g., 'anthropic:claude-sonnet-4').
        The actual model validity is checked at runtime by the API.

        Raises:
            ValueError: If format is invalid.
        """
        if ":" not in v:
            msg = f"Model must be in 'provider:model-id' format, got: {v}"
            raise ValueError(msg)
        provider, model_id = v.split(":", 1)
        if not provider or not model_id:
            msg = f"Both provider and model-id are required, got: {v}"
            raise ValueError(msg)
        return v

    def save(self) -> None:
        """Persist current config to file.

        Creates the config directory if it doesn't exist.
        """
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict()
        path.write_text(tomli_w.dumps(data))

    def _to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {"model": self.model}

    @classmethod
    def load(cls) -> "MemexConfig":
        """Load config with full precedence chain.

        Precedence (highest to lowest):
            1. Environment variables (MEMEX_*)
            2. Config file
            3. Defaults

        Returns:
            Loaded configuration.
        """
        config_path = get_config_path()
        file_values: dict[str, Any] = {}

        if config_path.exists():
            content = config_path.read_text()
            if content.strip():
                file_values = tomllib.loads(content)

        # Only use file values for fields not set by env vars
        # (env vars take precedence)
        effective_values: dict[str, Any] = {}
        for key, value in file_values.items():
            env_key = f"MEMEX_{key.upper()}"
            if env_key not in os.environ:
                effective_values[key] = value

        return cls(**effective_values)
