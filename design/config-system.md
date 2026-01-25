# Configuration System Design

**Issue**: memex-9ci
**Status**: Draft
**Author**: Agent

## Overview

Establish a configuration system for memex that:
1. Enables model selection without code changes
2. Provides a pattern for future settings
3. Supports layered precedence (env vars > file > defaults)
4. Offers interactive CLI for discoverability

## Architecture

### Precedence (highest to lowest)

```
CLI flags  →  Environment vars  →  Config file  →  Defaults
```

### Core Components

```
src/memex/
├── config.py          # NEW: MemexConfig settings class
└── cli.py             # MODIFY: add `mx config` subcommand
```

### Config File Location

```
$MEMEX_HOME/config.toml    # Default: ~/.memex/config.toml
```

Lives alongside the database for portability.

## Implementation

### 1. Settings Class (`src/memex/config.py`)

```python
"""Memex configuration management."""

import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_memex_home() -> Path:
    """Return the memex home directory."""
    return Path(os.environ.get("MEMEX_HOME", "~/.memex")).expanduser()


def get_config_path() -> Path:
    """Return the config file path."""
    return get_memex_home() / "config.toml"


class MemexConfig(BaseSettings):
    """Memex configuration with layered precedence.

    Precedence (highest to lowest):
        1. Environment variables (MEMEX_*)
        2. Config file ($MEMEX_HOME/config.toml)
        3. Defaults defined here
    """

    model_config = SettingsConfigDict(
        env_prefix="MEMEX_",
        toml_file=get_config_path(),  # Note: need to handle dynamically
    )

    # LLM model to use (provider:model-id format)
    model: str = "anthropic:claude-sonnet-4-20250514"

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        """Validate model string format without enumerating all models."""
        if ":" not in v:
            raise ValueError(
                f"Model must be in 'provider:model-id' format, got: {v}"
            )
        provider, model_id = v.split(":", 1)
        if not provider or not model_id:
            raise ValueError(
                f"Both provider and model-id required, got: {v}"
            )
        return v

    def save(self) -> None:
        """Persist current config to file."""
        import tomli_w

        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        # Only save non-default values? Or all?
        # Starting with all for transparency
        data = {"model": self.model}
        path.write_text(tomli_w.dumps(data))
```

**Open question**: pydantic-settings `toml_file` is evaluated at class definition time. Need to handle the dynamic `$MEMEX_HOME` path. Options:
- Custom settings source
- Factory function that sets config before loading
- Post-load overlay

### 2. CLI Commands (`mx config`)

```python
# In cli.py

@cli.group()
def config():
    """View and modify memex configuration."""
    pass


@config.command("get")
@click.argument("key", required=False)
def config_get(key: str | None):
    """Show configuration value(s).

    \b
    Examples:
        mx config get          Show all settings
        mx config get model    Show current model
    """
    cfg = MemexConfig()

    if key is None:
        # Show all config
        click.echo(f"model = {cfg.model}")
        click.echo(f"\n(Config file: {get_config_path()})")
    elif hasattr(cfg, key):
        click.echo(getattr(cfg, key))
    else:
        click.echo(f"Unknown config key: {key}", err=True)
        raise SystemExit(1)


@config.command("set")
@click.argument("key")
@click.argument("value", required=False)
def config_set(key: str, value: str | None):
    """Set a configuration value.

    If value is omitted, shows an interactive picker (where available).

    \b
    Examples:
        mx config set model                     Interactive picker
        mx config set model anthropic:claude-opus-4-20250514
    """
    cfg = MemexConfig()

    if key == "model":
        if value is None:
            value = _interactive_model_picker(current=cfg.model)
            if value is None:
                click.echo("Cancelled")
                return

        # Validate before saving
        try:
            cfg = MemexConfig(model=value)
        except ValueError as e:
            click.echo(f"Invalid value: {e}", err=True)
            raise SystemExit(1)

        cfg.save()
        click.echo(f"Set model = {value}")
    else:
        click.echo(f"Unknown config key: {key}", err=True)
        raise SystemExit(1)


def _interactive_model_picker(current: str) -> str | None:
    """Show interactive model selection with questionary."""
    import questionary

    # Common models to show (not exhaustive - user can pick "Other")
    choices = [
        questionary.Choice(
            "claude-sonnet-4 (recommended)",
            value="anthropic:claude-sonnet-4-20250514",
        ),
        questionary.Choice(
            "claude-opus-4",
            value="anthropic:claude-opus-4-20250514",
        ),
        questionary.Choice(
            "claude-haiku-3.5",
            value="anthropic:claude-haiku-3-5-20241022",
        ),
        questionary.Separator(),
        questionary.Choice(
            "Other (enter manually)",
            value="_other",
        ),
    ]

    # Mark current selection
    result = questionary.select(
        "Select model:",
        choices=choices,
        default=current if current in [c.value for c in choices if hasattr(c, 'value')] else None,
    ).ask()

    if result is None:
        return None  # User cancelled (Ctrl+C)

    if result == "_other":
        result = questionary.text(
            "Enter model (provider:model-id):",
            default=current,
        ).ask()

    return result
```

### 3. Wire Up Agent Creation

```python
# In cli.py, modify chat command

@cli.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Start interactive chat with memex."""
    if not _check_api_key():
        # ... existing error handling

    cfg = MemexConfig()  # Load config with precedence

    db_path: Path = ctx.obj["db_path"]
    db = Database(db_path)
    agent = create_agent(cfg.model)  # Use configured model

    _run_chat_loop(agent, db)
```

### 4. Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing
    "pydantic-settings>=2.0",
    "questionary>=2.0",
    "tomli-w>=1.0",  # For writing TOML
]
```

Note: Python 3.11+ has `tomllib` for reading, but writing requires `tomli-w`.

## File Layout

After implementation:

```
~/.memex/
├── memex.db          # Database
├── config.toml       # User configuration
├── .mx_history       # CLI history (existing)
└── archive/          # Backups (existing)
```

Example `config.toml`:

```toml
model = "anthropic:claude-opus-4-20250514"
```

## Test Plan

1. **Unit tests** (`tests/test_config.py`):
   - Default values load correctly
   - TOML file overrides defaults
   - Env vars override TOML
   - Model format validation works
   - Invalid model format raises

2. **Integration tests**:
   - `mx config get` shows current config
   - `mx config set model <value>` persists
   - `mx chat` uses configured model (mock API)

3. **Manual testing**:
   - Interactive picker UX
   - Error messages for invalid input

## Migration

No migration needed - purely additive:
- Existing users: continue using defaults
- Config file created on first `mx config set`

## Future Extensions

This pattern extends naturally to other settings:

```python
class MemexConfig(BaseSettings):
    model: str = "anthropic:claude-sonnet-4-20250514"

    # Future settings
    # cache_enabled: bool = True
    # max_context_tokens: int = 100000
    # archive_retention_days: int = 30
```

## Tasks

1. [ ] Add dependencies to pyproject.toml
2. [ ] Create `src/memex/config.py` with MemexConfig
3. [ ] Handle dynamic MEMEX_HOME in pydantic-settings
4. [ ] Add `mx config` CLI group with get/set commands
5. [ ] Implement interactive model picker
6. [ ] Wire config into `mx chat`
7. [ ] Write tests
8. [ ] Update .env.example with MEMEX_MODEL
9. [ ] Update CLI documentation
