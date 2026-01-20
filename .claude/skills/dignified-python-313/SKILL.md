---
name: dignified-python-313
description: Use when writing, reviewing, or refactoring Python 3.13+ code. Covers
  LBYL exception handling, modern type syntax (list[str], str | None), pathlib operations,
  ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level.
source: https://github.com/dagster-io/erk/tree/main/.claude/skills/dignified-python-313
note: Vendored and modified from dagster-io/erk. Removed erk-specific references and typechecker opinions.
---

# Dignified Python - Python 3.13 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@dignified-python-core.md
@type-annotations-common.md
@type-annotations-delta.md

## Version-Specific Checklist

@checklist.md

## Conditional Loading (Load Based on Task Patterns)

Core files above cover 80%+ of Python code patterns. Only load these additional files when you detect specific patterns:

Pattern detection examples:

- If task mentions "click" or "CLI" → Load `cli-patterns.md`
- If task mentions "subprocess" → Load `subprocess.md`

## How to Use This Skill

1. **Core knowledge** is loaded automatically (LBYL, pathlib, ABC, imports, exceptions)
2. **Type annotations** are loaded automatically (common syntax + Python 3.13 specific features)
3. **Additional patterns** may require extra loading (CLI patterns, subprocess)
4. **Each file is self-contained** with complete guidance for its domain

