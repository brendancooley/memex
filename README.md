# Memex

Personal knowledge management system.

## Installation

```bash
./scripts/bootstrap
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
