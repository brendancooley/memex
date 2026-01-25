"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from memex.config import MemexConfig, get_config_path, get_memex_home


class TestGetMemexHome:
    """Tests for get_memex_home function."""

    def test_returns_default_when_env_unset(self) -> None:
        """Returns ~/.memex when MEMEX_HOME is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MEMEX_HOME", None)
            home = get_memex_home()
            assert home == Path.home() / ".memex"

    def test_returns_env_var_when_set(self, tmp_path: Path) -> None:
        """Returns MEMEX_HOME value when set."""
        custom_home = tmp_path / "custom_memex"
        with patch.dict(os.environ, {"MEMEX_HOME": str(custom_home)}):
            home = get_memex_home()
            assert home == custom_home


class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_config_in_memex_home(self, tmp_path: Path) -> None:
        """Config path is config.toml in MEMEX_HOME."""
        custom_home = tmp_path / "memex"
        with patch.dict(os.environ, {"MEMEX_HOME": str(custom_home)}):
            path = get_config_path()
            assert path == custom_home / "config.toml"


class TestMemexConfigDefaults:
    """Tests for MemexConfig default values."""

    def test_default_model(self) -> None:
        """Default model is claude-sonnet-4."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MEMEX_MODEL", None)
            cfg = MemexConfig()
            assert cfg.model == "anthropic:claude-sonnet-4-20250514"


class TestMemexConfigValidation:
    """Tests for MemexConfig model validation."""

    def test_valid_model_format_accepted(self) -> None:
        """Valid provider:model-id format is accepted."""
        cfg = MemexConfig(model="anthropic:claude-opus-4-20250514")
        assert cfg.model == "anthropic:claude-opus-4-20250514"

    def test_missing_colon_rejected(self) -> None:
        """Model without colon is rejected."""
        with pytest.raises(ValueError, match="provider:model-id"):
            MemexConfig(model="invalid-model")

    def test_empty_provider_rejected(self) -> None:
        """Empty provider is rejected."""
        with pytest.raises(ValueError, match="provider and model-id"):
            MemexConfig(model=":model-id")

    def test_empty_model_id_rejected(self) -> None:
        """Empty model-id is rejected."""
        with pytest.raises(ValueError, match="provider and model-id"):
            MemexConfig(model="anthropic:")


class TestMemexConfigEnvOverride:
    """Tests for environment variable override."""

    def test_env_var_overrides_default(self) -> None:
        """MEMEX_MODEL env var overrides default."""
        with patch.dict(
            os.environ, {"MEMEX_MODEL": "anthropic:claude-opus-4-20250514"}
        ):
            cfg = MemexConfig()
            assert cfg.model == "anthropic:claude-opus-4-20250514"

    def test_invalid_env_var_raises(self) -> None:
        """Invalid MEMEX_MODEL env var raises validation error."""
        with (
            patch.dict(os.environ, {"MEMEX_MODEL": "invalid"}),
            pytest.raises(ValueError),
        ):
            MemexConfig()


class TestMemexConfigFileLoading:
    """Tests for config file loading."""

    def test_loads_from_file(self, tmp_path: Path) -> None:
        """Config loads values from TOML file."""
        config_dir = tmp_path / "memex"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('model = "anthropic:claude-opus-4-20250514"\n')

        with patch.dict(os.environ, {"MEMEX_HOME": str(config_dir)}, clear=True):
            os.environ.pop("MEMEX_MODEL", None)
            cfg = MemexConfig.load()
            assert cfg.model == "anthropic:claude-opus-4-20250514"

    def test_env_var_overrides_file(self, tmp_path: Path) -> None:
        """Environment variable takes precedence over file."""
        config_dir = tmp_path / "memex"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('model = "anthropic:claude-opus-4-20250514"\n')

        with patch.dict(
            os.environ,
            {
                "MEMEX_HOME": str(config_dir),
                "MEMEX_MODEL": "anthropic:claude-haiku-3-5-20241022",
            },
        ):
            cfg = MemexConfig.load()
            assert cfg.model == "anthropic:claude-haiku-3-5-20241022"

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        """Missing config file uses defaults."""
        config_dir = tmp_path / "memex"
        config_dir.mkdir()
        # No config.toml created

        with patch.dict(os.environ, {"MEMEX_HOME": str(config_dir)}, clear=True):
            os.environ.pop("MEMEX_MODEL", None)
            cfg = MemexConfig.load()
            assert cfg.model == "anthropic:claude-sonnet-4-20250514"


class TestMemexConfigSave:
    """Tests for config persistence."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() creates config file."""
        config_dir = tmp_path / "memex"
        # Directory doesn't exist yet

        with patch.dict(os.environ, {"MEMEX_HOME": str(config_dir)}):
            cfg = MemexConfig(model="anthropic:claude-opus-4-20250514")
            cfg.save()

            config_file = config_dir / "config.toml"
            assert config_file.exists()
            content = config_file.read_text()
            assert 'model = "anthropic:claude-opus-4-20250514"' in content

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        """save() overwrites existing config file."""
        config_dir = tmp_path / "memex"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text('model = "anthropic:claude-opus-4-20250514"\n')

        with patch.dict(os.environ, {"MEMEX_HOME": str(config_dir)}):
            cfg = MemexConfig(model="anthropic:claude-haiku-3-5-20241022")
            cfg.save()

            content = config_file.read_text()
            assert "claude-haiku-3-5-20241022" in content
            assert "claude-opus-4" not in content

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Config can be saved and loaded back."""
        config_dir = tmp_path / "memex"

        with patch.dict(os.environ, {"MEMEX_HOME": str(config_dir)}, clear=True):
            os.environ.pop("MEMEX_MODEL", None)

            # Save
            cfg1 = MemexConfig(model="anthropic:claude-opus-4-20250514")
            cfg1.save()

            # Load
            cfg2 = MemexConfig.load()
            assert cfg2.model == cfg1.model
