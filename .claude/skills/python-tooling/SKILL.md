---
name: python-tooling
description: Use when scaffolding new Python projects, setting up development environments,
  configuring testing/linting/formatting, or managing dependencies with uv. Covers
  pyproject.toml configuration, pytest, ruff, pre-commit hooks, and modern Python
  project best practices.
vendored_from: https://pydevtools.com/handbook/explanation/modern-python-project-setup-guide-for-ai-assistants/
---

# Python Project Scaffolding Guide

This guide provides a standardized approach to scaffolding Python projects using modern tooling.

## Core Philosophy

Python project setup should be:

- **Automated**: Minimize manual configuration steps
- **Standardized**: Use PEP 621 compliant pyproject.toml
- **Reproducible**: Lock dependencies for consistent environments
- **Quality-focused**: Include linting, formatting, and testing from the start
- **Isolated**: Use `uv run` and `uvx` to ensure all operations happen within project environments

> **Tool Isolation with uv run and uvx**: Always prefer `uv run <command>` (for dev dependencies) and `uvx <command>` (for installing one-off tools like pre-commit) to ensure all operations happen within the project's isolated and locked environment.

## Decision Tree

**Step 1: Determine Project Type**

- Is this a library/package for distribution? → Use `uv init --package`
- Is this an application/script/service? → Use `uv init`

**Step 2: Add Runtime Dependencies**

- Does the project need external packages? → Use `uv add <package>`

**Step 3: Configure Development Tools** (in order)

1. Setup pytest for testing
2. Setup ruff for linting/formatting
3. Setup pre-commit hooks for automation

**Step 4: Document Usage**

- Create comprehensive README.md
- Document installation and development workflow

## Standard Project Initialization

### 1. Create Project Structure

**For applications** (scripts, services, tools):

```bash
uv init project-name
cd project-name
```

**For packages** (libraries, distributable code):

```bash
uv init project-name --package
cd project-name
```

> Use `--package` when creating code meant to be imported by other projects or published to PyPI.

### 2. Add Runtime Dependencies

```bash
# Add dependencies as needed
uv add requests pandas

# Specify version constraints when needed
uv add "django>=4.2,<5.0"
```

### 3. Configure Testing with pytest

```bash
# Add pytest as development dependency
uv add --dev pytest pytest-cov
```

Create `tests/` directory:

```bash
mkdir tests
```

> Modern pytest doesn't require `tests/__init__.py` - the directory structure alone is sufficient for test discovery.

Add pytest configuration to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
]
```

### 4. Configure Ruff for Linting and Formatting

```bash
# Add ruff as development dependency
uv add --dev ruff
```

Add ruff configuration to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line length (handled by formatter)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### 5. Setup Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.11
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
```

Install hooks:

```bash
uvx pre-commit install
```

### 6. Create Standard Project Files

**README.md template:**

````markdown
# Project Name

Brief description of what the project does.

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python -m project_name
```

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```
````

**Extend .gitignore** (if needed beyond what `uv init` provides):

```
# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo
```

## Project Type Patterns

### CLI Tool Pattern

```bash
uv init cli-tool --package
cd cli-tool
uv add click  # or typer, argparse
uv add --dev pytest
```

Add CLI entry point in `pyproject.toml`:

```toml
[project.scripts]
cli-tool = "cli_tool.main:cli"
```

### Web Application Pattern

```bash
uv init web-app
cd web-app
uv add fastapi uvicorn  # or django, flask
uv add --dev pytest pytest-asyncio httpx
```

### Data Science Pattern

```bash
uv init data-project
cd data-project
uv add pandas numpy matplotlib jupyter
uv add --dev pytest pytest-cov
```

## Quality Assurance Checklist

Before completing project setup, verify:

- [ ] `pyproject.toml` contains all metadata
- [ ] `uv.lock` is generated
- [ ] `.gitignore` excludes virtual environments and cache files
- [ ] `README.md` documents installation and usage
- [ ] Tests directory exists
- [ ] Pre-commit hooks are installed
- [ ] `uv run ruff check .` passes without errors
- [ ] `uv run pytest` discovers and runs tests successfully

## Type Checking with Pyright

```bash
uv add --dev pyright
```

Run type checking:

```bash
uv run pyright
```

Configure in `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.13"
```

## CI/CD Configuration

Example GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
      - name: Run linter
        run: uv run ruff check .
```

## Anti-Patterns to Avoid

**Don't:**

- Mix pip and uv in the same project
- Run tools globally instead of with `uv run` or `uvx`
- Commit `uv.lock` for libraries (do commit for applications)
- Use `requirements.txt` with uv projects
- Manually create virtual environments (uv handles this)
- Skip lockfiles for reproducibility

**Do:**

- Use `uv add` for all dependency management
- Use `uv run` for dev dependencies, `uvx` for one-off tools
- Commit `uv.lock` for applications and CLIs
- Use `[tool.uv]` section for development dependencies
- Let uv manage virtual environments automatically
- Pin Python versions in `pyproject.toml`

## Workflow Commands Reference

```bash
# Development workflow
uv run pytest                    # Run tests
uv run pytest --cov             # Run with coverage
uv run ruff check .             # Lint code
uv run ruff check --fix .       # Lint and auto-fix
uv run ruff format .            # Format code

# Dependency management
uv add package-name             # Add runtime dependency
uv add --dev package-name       # Add dev dependency
uv remove package-name          # Remove dependency
uv sync                         # Sync environment with lockfile
uv lock                         # Update lockfile

# Project execution
uv run python script.py         # Run script
uv run python -m module         # Run module
uv run --with package cmd       # Run with temporary dependency

# One-off tool execution
uvx pre-commit install          # Install pre-commit hooks
uvx black .                     # Run black without adding to project
```

## VS Code Configuration

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  }
}
```
