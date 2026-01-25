# Project Vision

Memex is a personal knowledge system—a second brain you talk to like your first.

Two pillars: a **structured database** for queryable entities (people, events, todos) and an **unstructured scratchpad** for exploratory thinking (markdown docs with wikilinks). An LLM serves as the interface—you speak naturally, it files and retrieves.

Key insight: **writes are casual, reads are synthesized.** Jot fragments as they come. When you need context for a decision, the system weaves those fragments into a coherent picture.

The schema evolves through use—no upfront design. The first time you mention a person, it proposes a Person table.

# Principles

## Workflow

- commit to develop, human will do periodic syncs to main for review/release
- keep commits small and atomic. aggressively break down larger tasks and create new issues to track unfinished work as needed
- when instructions are not clear or unforseen obstacles are detected, always return to your supervisor (human or agent) for clarification
- write user-facing documentation for all new features first. for most features, write tests next, and then implementation code. break into separate tasks for each level of the hierarchy as needed.
- make all environmental changes reproducible via boostrap/etc scripts. new developers should always be able to reproduce the development enviroment programmatically on a new machine.

## Documentation

- `docs/` is for **user-facing** documentation (published via mkdocs)
- `design/` is for **internal** design docs, specs, and planning artifacts
- do not create documentation files unless explicitly requested

## Hygiene

- conventional commits

## Testing

- test structure mirrors src structure: `tests/` should reflect `src/memex/` hierarchy
  - `src/memex/db/` → `tests/db/`
  - `src/memex/ops/schema.py` → `tests/ops/test_schema.py`
- each module gets a corresponding test module
- use `pytest` fixtures for shared setup (db connections, temp directories)
- for LLM agent tests, use pydantic-ai's `TestModel` to mock responses deterministically

## Stack

- astral stack for tooling: `uv`, `ruff`, `ty`
  - load the `python-tooling` skill when working with python tools
  - lint and typecheck aggressively, add optional rules to steer agents toward best practices and thoughtful abstractions
- modern (typed) python, load the `dignified-python-313` skill when developing
- `direnv` for environment management

# Agent Instructions (Beads)

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
