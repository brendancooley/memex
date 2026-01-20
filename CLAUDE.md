# Principles

## Workflow

- commit to develop, human will do periodic syncs to main for review/release
- keep commits small and atomic. aggressively break down larger tasks and create new issues to track unfinished work as needed
- when instructions are not clear or unforseen obstacles are detected, always return to your supervisor (human or agent) for clarification
- write user-facing documentation for all new features first. for most features, write tests next, and then implementation code
- make all environmental changes reproducible via boostrap/etc scripts. new developers should always be able to reproduce the development enviroment programmatically on a new machine.

## Stack

- astral stack for tooling: `uv`, `ruff`, `ty`
  - lint and typecheck aggressively, add optional rules to steer agents toward best practices and thoughtful abstractions
- modern (typed) python, load the dignified-python-313 skill when developing
- direnv for environment management

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
