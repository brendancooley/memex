# Memex

Personal knowledge management system.

## Installation

```bash
./scripts/bootstrap
```

## Environment Setup

This project uses [direnv](https://direnv.net/) to load environment variables from `.env`. After installing direnv, add the shell hook:

```bash
# Add to ~/.zshrc (or ~/.bashrc for bash)
grep -q "direnv hook" ~/.zshrc || echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
```

Then allow the project's `.envrc`:

```bash
direnv allow
```

## Development

```bash
# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check
```

## Branch Workflow

Two branches with different purposes:

- **develop** — sandbox for agents and day-to-day work
- **main** — curated source of truth, synced periodically for releases

### Syncing develop → main

```bash
# Create PR from develop to main
./scripts/sync-to-main

# After PR is merged, sync main back into develop
./scripts/sync-to-main --post
```

Use **"Create a merge commit"** (not squash) when merging to preserve history on both branches.
