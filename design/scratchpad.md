# Scratchpad Design

**Issue**: memex-03k
**Status**: Draft
**Author**: Agent

## Overview

The scratchpad is the second pillar of Memex—a collection of markdown files for unstructured thinking. While the database stores queryable entities (people, events, todos), the scratchpad holds exploratory content: research threads, deliberations, notes that resist structure.

Key properties:
- **Casual writes**: Append thoughts without organizing upfront
- **Synthesized reads**: Agent weaves fragments into context when needed
- **Wikilinks**: `[[doc-name]]` connects documents to each other
- **Entity references**: Natural language mentions resolve to database records

## File Layout

```
$MEMEX_HOME/scratchpad/
├── preschool-search.md
├── career-thoughts.md
├── reading/
│   ├── attention-paper.md
│   └── book-club.md
└── scratch.md
```

- All documents are markdown (`.md` extension enforced)
- Subdirectories allowed for organization
- Paths are relative to `scratchpad/` root
- `MEMEX_HOME` defaults to `~/.memex`

## Document Metadata

Documents use YAML frontmatter for metadata:

```markdown
---
created: 2026-02-03T10:30:00
updated: 2026-02-03T14:15:00
tags: [preschool, decisions]
status: active
---

# Preschool Search

Content here...
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `created` | ISO datetime | Set automatically on first write |
| `updated` | ISO datetime | Updated automatically on every write/append |
| `tags` | list[str] | User-defined categories |
| `status` | str | Workflow state: `active`, `archived`, `draft` |

### Behavior

- **Write**: If no frontmatter exists, add it with `created` and `updated`
- **Write**: If frontmatter exists, update `updated` timestamp
- **Append**: Update `updated` timestamp
- **Read**: Parse and return metadata alongside content
- **List**: Include tags and status in `DocumentInfo`

### Implementation

```python
import re
from datetime import datetime

import yaml

_FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

@dataclass
class DocumentMetadata:
    """Parsed frontmatter metadata."""
    created: datetime
    updated: datetime
    tags: list[str] = field(default_factory=list)
    status: str = "active"

def parse_frontmatter(content: str) -> tuple[DocumentMetadata | None, str]:
    """Parse frontmatter from content, return (metadata, body)."""
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, content

    try:
        data = yaml.safe_load(match.group(1))
        metadata = DocumentMetadata(
            created=data.get("created", datetime.now()),
            updated=data.get("updated", datetime.now()),
            tags=data.get("tags", []),
            status=data.get("status", "active"),
        )
        body = content[match.end():]
        return metadata, body
    except yaml.YAMLError:
        return None, content

def add_frontmatter(content: str, metadata: DocumentMetadata) -> str:
    """Add or update frontmatter in content."""
    _, body = parse_frontmatter(content)

    frontmatter = yaml.dump({
        "created": metadata.created.isoformat(),
        "updated": metadata.updated.isoformat(),
        "tags": metadata.tags,
        "status": metadata.status,
    }, default_flow_style=None, sort_keys=False)

    return f"---\n{frontmatter}---\n{body}"
```

## Operations

### Pydantic Models

```python
# src/memex/scratchpad/ops.py

from pydantic import BaseModel, field_validator

class Read(BaseModel):
    """Read a scratchpad document."""
    path: str  # e.g., "preschool-search.md" or "reading/book-club.md"

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        # See Path Validation section
        ...

class Write(BaseModel):
    """Create or overwrite a scratchpad document."""
    path: str
    content: str

class Append(BaseModel):
    """Append content to an existing document."""
    path: str
    content: str

class List(BaseModel):
    """List all scratchpad documents."""
    pass  # No parameters

class Search(BaseModel):
    """Search documents by keyword."""
    query: str

class Delete(BaseModel):
    """Delete a scratchpad document."""
    path: str

class Move(BaseModel):
    """Move/rename a scratchpad document."""
    old_path: str
    new_path: str
```

### Executor Function

Following the pattern from `ops/query.py`:

```python
from pathlib import Path
from typing import overload

@overload
def execute(root: Path, op: Read) -> str: ...

@overload
def execute(root: Path, op: Write) -> None: ...

@overload
def execute(root: Path, op: Append) -> None: ...

@overload
def execute(root: Path, op: List) -> list[DocumentInfo]: ...

@overload
def execute(root: Path, op: Search) -> list[SearchResult]: ...

@overload
def execute(root: Path, op: Delete) -> None: ...

@overload
def execute(root: Path, op: Move) -> None: ...

def execute(root: Path, op: Read | Write | Append | List | Search | Delete | Move) -> ...:
    """Execute a scratchpad operation."""
    ...
```

### Return Types

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DocumentInfo:
    """Metadata about a scratchpad document."""
    path: str                    # Relative path from scratchpad root
    title: str | None            # First H1 heading, if present
    created: datetime            # From frontmatter, or file ctime
    updated: datetime            # From frontmatter, or file mtime
    size: int                    # Size in bytes
    tags: list[str]              # From frontmatter
    status: str                  # From frontmatter (default: "active")

@dataclass
class SearchResult:
    """A search match within a document."""
    path: str
    snippet: str        # Context around the match
    line: int           # Line number of match
```

## Path Validation

Paths must be validated to prevent directory traversal attacks and ensure consistency.

### Rules

1. **No absolute paths**: Must not start with `/`
2. **No traversal**: Must not contain `..`
3. **No hidden files**: Must not start with `.` or contain `/.`
4. **Markdown only**: Must end with `.md`
5. **Valid characters**: Alphanumeric, hyphen, underscore, forward slash
6. **No double slashes**: Must not contain `//`
7. **Normalized**: Leading/trailing slashes stripped

### Implementation

```python
import re

_VALID_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_\-/]+\.md$")

def validate_path(path: str) -> str:
    """Validate and normalize a scratchpad path.

    Args:
        path: Relative path to validate.

    Returns:
        Normalized path.

    Raises:
        ValueError: If path is invalid.
    """
    # Strip leading/trailing slashes and whitespace
    normalized = path.strip().strip("/")

    # Check for traversal attempts
    if ".." in normalized:
        raise ValueError(f"Path traversal not allowed: {path!r}")

    # Check for hidden files
    if normalized.startswith(".") or "/." in normalized:
        raise ValueError(f"Hidden files not allowed: {path!r}")

    # Check for double slashes
    if "//" in normalized:
        raise ValueError(f"Invalid path (double slash): {path!r}")

    # Must be markdown
    if not normalized.endswith(".md"):
        raise ValueError(f"Only .md files allowed: {path!r}")

    # Validate characters
    if not _VALID_PATH_PATTERN.match(normalized):
        raise ValueError(f"Invalid path characters: {path!r}")

    return normalized
```

## Operation Details

### Read

```python
def _execute_read(root: Path, op: Read) -> str:
    """Read document content."""
    full_path = root / op.path

    if not full_path.exists():
        raise FileNotFoundError(f"Document not found: {op.path}")

    return full_path.read_text(encoding="utf-8")
```

**Behavior**:
- Returns full document content as string
- Raises `FileNotFoundError` if document doesn't exist
- UTF-8 encoding assumed

### Write

```python
def _execute_write(root: Path, op: Write) -> None:
    """Create or overwrite a document."""
    full_path = root / op.path

    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)

    full_path.write_text(op.content, encoding="utf-8")
```

**Behavior**:
- Creates document if it doesn't exist
- Overwrites if it does (no confirmation—agent should confirm with user)
- Creates parent directories automatically
- UTF-8 encoding

### Append

```python
def _execute_append(root: Path, op: Append) -> None:
    """Append content to an existing document."""
    full_path = root / op.path

    if not full_path.exists():
        raise FileNotFoundError(f"Document not found: {op.path}")

    # Ensure newline separation
    existing = full_path.read_text(encoding="utf-8")
    separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
    if existing and not existing.endswith("\n"):
        separator = "\n\n"

    full_path.write_text(existing + separator + op.content, encoding="utf-8")
```

**Behavior**:
- Fails if document doesn't exist (use Write to create)
- Adds appropriate newline separation
- Common use: adding observations to an ongoing thread

### List

```python
def _execute_list(root: Path, op: List) -> list[DocumentInfo]:
    """List all documents with metadata."""
    results = []

    for md_file in root.rglob("*.md"):
        rel_path = md_file.relative_to(root)
        stat = md_file.stat()

        # Extract title from first H1
        title = _extract_title(md_file)

        results.append(DocumentInfo(
            path=str(rel_path),
            title=title,
            modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
        ))

    # Sort by modification time (newest first)
    return sorted(results, key=lambda d: d.modified, reverse=True)

def _extract_title(path: Path) -> str | None:
    """Extract first H1 heading from markdown file."""
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
            # Stop after first non-empty, non-heading line
            if line.strip() and not line.startswith("#"):
                break
    return None
```

**Behavior**:
- Recursively finds all `.md` files
- Extracts title from first `# Heading`
- Returns sorted by modification time (newest first)
- Used by agent to show available documents in context

### Search

```python
def _execute_search(root: Path, op: Search) -> list[SearchResult]:
    """Search documents by keyword."""
    results = []
    query_lower = op.query.lower()

    for md_file in root.rglob("*.md"):
        rel_path = str(md_file.relative_to(root))

        with md_file.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if query_lower in line.lower():
                    results.append(SearchResult(
                        path=rel_path,
                        snippet=_create_snippet(line, op.query),
                        line=line_num,
                    ))

    return results

def _create_snippet(line: str, query: str, context_chars: int = 50) -> str:
    """Create a snippet with context around the match."""
    # Find match position (case-insensitive)
    idx = line.lower().find(query.lower())
    start = max(0, idx - context_chars)
    end = min(len(line), idx + len(query) + context_chars)

    snippet = line[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(line):
        snippet = snippet + "..."

    return snippet
```

**Behavior**:
- Case-insensitive keyword search
- Returns all matches with line numbers
- Snippets provide context around matches
- Future: upgrade to full-text search or semantic search

### Delete

```python
def _execute_delete(root: Path, op: Delete) -> None:
    """Delete a document."""
    full_path = root / op.path

    if not full_path.exists():
        raise FileNotFoundError(f"Document not found: {op.path}")

    full_path.unlink()

    # Clean up empty parent directories
    parent = full_path.parent
    while parent != root and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
```

**Behavior**:
- Fails if document doesn't exist
- Cleans up empty parent directories after deletion
- Agent should confirm with user before deleting

### Move

```python
def _execute_move(root: Path, op: Move) -> None:
    """Move/rename a document."""
    old_full = root / op.old_path
    new_full = root / op.new_path

    if not old_full.exists():
        raise FileNotFoundError(f"Document not found: {op.old_path}")

    if new_full.exists():
        raise FileExistsError(f"Destination already exists: {op.new_path}")

    # Create parent directories if needed
    new_full.parent.mkdir(parents=True, exist_ok=True)

    old_full.rename(new_full)

    # Clean up empty parent directories
    parent = old_full.parent
    while parent != root and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
```

**Behavior**:
- Fails if source doesn't exist
- Fails if destination already exists (no silent overwrite)
- Creates parent directories for destination
- Cleans up empty source directories
- Useful for agent to reorganize documents

## Wikilinks (Future Enhancement)

Wikilinks connect documents: `[[career-thoughts]]` links to `career-thoughts.md`.

### Syntax

```markdown
See also [[career-thoughts]] for timing considerations.
Sarah recommended this—see [[conversations/sarah-coffee]].
```

### Resolution Rules

1. Exact match: `[[foo]]` → `foo.md`
2. With extension: `[[foo.md]]` → `foo.md`
3. Subdirectory: `[[reading/book]]` → `reading/book.md`
4. Case-insensitive matching as fallback

### Parsing

```python
import re

_WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

def extract_wikilinks(content: str) -> list[str]:
    """Extract all wikilink targets from content."""
    return _WIKILINK_PATTERN.findall(content)

def resolve_wikilink(root: Path, link: str) -> Path | None:
    """Resolve a wikilink to a file path, or None if not found."""
    # Normalize: strip extension if present
    target = link.removesuffix(".md")

    # Try exact match
    candidate = root / f"{target}.md"
    if candidate.exists():
        return candidate

    # Try case-insensitive
    for md_file in root.rglob("*.md"):
        if md_file.stem.lower() == target.lower():
            return md_file

    return None
```

### Backlinks

When reading a document, the agent can query for backlinks:

```python
def find_backlinks(root: Path, target_path: str) -> list[str]:
    """Find documents that link to the target."""
    target_stem = Path(target_path).stem
    backlinks = []

    for md_file in root.rglob("*.md"):
        if str(md_file.relative_to(root)) == target_path:
            continue  # Skip self

        content = md_file.read_text(encoding="utf-8")
        links = extract_wikilinks(content)

        for link in links:
            if link.removesuffix(".md") == target_stem:
                backlinks.append(str(md_file.relative_to(root)))
                break

    return backlinks
```

**Note**: Wikilink support is a P2 feature (memex-aei). Core operations ship without it.

## Agent Integration

### Tool Registration

```python
# In agent.py

@agent.tool
async def scratchpad_read(ctx: RunContext[AgentDeps], path: str) -> str:
    """Read a scratchpad document.

    Args:
        path: Document path relative to scratchpad/ (e.g., "notes.md")
    """
    op = scratchpad_ops.Read(path=path)
    return scratchpad_ops.execute(ctx.deps.scratchpad_root, op)

@agent.tool
async def scratchpad_write(
    ctx: RunContext[AgentDeps], path: str, content: str
) -> str:
    """Create or update a scratchpad document.

    Args:
        path: Document path relative to scratchpad/
        content: Full document content (markdown)
    """
    op = scratchpad_ops.Write(path=path, content=content)
    scratchpad_ops.execute(ctx.deps.scratchpad_root, op)
    return f"Written: {path}"

@agent.tool
async def scratchpad_append(
    ctx: RunContext[AgentDeps], path: str, content: str
) -> str:
    """Append content to an existing scratchpad document.

    Args:
        path: Document path relative to scratchpad/
        content: Content to append
    """
    op = scratchpad_ops.Append(path=path, content=content)
    scratchpad_ops.execute(ctx.deps.scratchpad_root, op)
    return f"Appended to: {path}"

@agent.tool
async def scratchpad_list(ctx: RunContext[AgentDeps]) -> str:
    """List all scratchpad documents."""
    op = scratchpad_ops.List()
    docs = scratchpad_ops.execute(ctx.deps.scratchpad_root, op)

    if not docs:
        return "No scratchpad documents yet."

    lines = ["Scratchpad documents:"]
    for doc in docs:
        title = f" - {doc.title}" if doc.title else ""
        lines.append(f"  {doc.path}{title}")
    return "\n".join(lines)

@agent.tool
async def scratchpad_search(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search scratchpad documents by keyword.

    Args:
        query: Search term
    """
    op = scratchpad_ops.Search(query=query)
    results = scratchpad_ops.execute(ctx.deps.scratchpad_root, op)

    if not results:
        return f"No matches for: {query}"

    lines = [f"Found {len(results)} match(es):"]
    for r in results[:10]:  # Limit output
        lines.append(f"  {r.path}:{r.line} - {r.snippet}")
    return "\n".join(lines)

@agent.tool
async def scratchpad_delete(ctx: RunContext[AgentDeps], path: str) -> str:
    """Delete a scratchpad document.

    Args:
        path: Document path relative to scratchpad/
    """
    op = scratchpad_ops.Delete(path=path)
    scratchpad_ops.execute(ctx.deps.scratchpad_root, op)
    return f"Deleted: {path}"

@agent.tool
async def scratchpad_move(
    ctx: RunContext[AgentDeps], old_path: str, new_path: str
) -> str:
    """Move or rename a scratchpad document.

    Args:
        old_path: Current document path
        new_path: New document path
    """
    op = scratchpad_ops.Move(old_path=old_path, new_path=new_path)
    scratchpad_ops.execute(ctx.deps.scratchpad_root, op)
    return f"Moved: {old_path} -> {new_path}"
```

### Context Injection

The agent's system prompt should include scratchpad awareness:

```python
# In context.py

def build_scratchpad_context(root: Path) -> str:
    """Build scratchpad summary for system prompt."""
    op = scratchpad_ops.List()
    docs = scratchpad_ops.execute(root, op)

    if not docs:
        return "Scratchpad: empty"

    lines = ["Scratchpad documents:"]
    for doc in docs[:10]:  # Limit to recent 10
        title = doc.title or "(untitled)"
        lines.append(f"  - {doc.path}: {title}")

    if len(docs) > 10:
        lines.append(f"  ... and {len(docs) - 10} more")

    return "\n".join(lines)
```

### When to Use Scratchpad vs Database

Add to system prompt:

```
Use the DATABASE for:
- Entities with clear structure (people, events, todos, places)
- Things you'll want to query ("list todos due this week")
- Facts with typed properties (dates, numbers, relationships)

Use the SCRATCHPAD for:
- Exploratory thinking and deliberation
- Research threads and notes
- Observations that don't fit a schema
- Anything the user says to "jot down" or "note"

WHEN INTENT IS AMBIGUOUS, ASK THE USER.
Example: "note that Sarah likes coffee" could mean:
  - Add to Sarah's database record (if Sarah exists)
  - Start a scratchpad note about Sarah
  - Append to an existing scratchpad doc
Ask: "Should I add this to Sarah's record, or start a scratchpad note?"

BEFORE DELETING, ALWAYS CONFIRM.
Example: "clean up old notes" - list what would be deleted and confirm.
```

## Module Structure

```
src/memex/
├── scratchpad/
│   ├── __init__.py      # Re-export public API
│   └── ops.py           # Operations and executor
└── ...

tests/
├── scratchpad/
│   └── test_ops.py      # Operation tests
└── ...
```

## Test Plan

### Unit Tests (`tests/scratchpad/test_ops.py`)

**Path validation**:
- Valid paths accepted
- Traversal (`..`) rejected
- Hidden files (`.foo`) rejected
- Non-markdown rejected
- Absolute paths rejected

**Read operation**:
- Reads existing document
- Raises FileNotFoundError for missing
- Returns metadata and content

**Write operation**:
- Creates new document with frontmatter
- Overwrites existing, updates `updated` timestamp
- Creates parent directories
- Rejects invalid YAML frontmatter
- Rejects binary content

**Append operation**:
- Appends to existing
- Raises FileNotFoundError for missing
- Proper newline handling
- Updates `updated` timestamp

**List operation**:
- Returns all documents
- Extracts titles correctly
- Includes metadata (tags, status, timestamps)
- Sorted by modification time

**Search operation**:
- Finds keyword matches
- Case-insensitive
- Returns snippets with context

**Delete operation**:
- Deletes existing document
- Raises FileNotFoundError for missing
- Cleans up empty parent directories

**Move operation**:
- Moves document to new path
- Raises FileNotFoundError for missing source
- Raises FileExistsError if destination exists
- Creates parent directories for destination
- Cleans up empty source directories

**Metadata/Frontmatter**:
- Parses valid frontmatter
- Handles missing frontmatter gracefully
- Adds frontmatter to new documents
- Preserves existing frontmatter fields on update

### Integration Tests

- Agent can create and read documents
- Agent chooses scratchpad vs database appropriately (mocked LLM)
- Documents persist across sessions

## Version Control (v1)

**Deferred to v1** - MVP ships without versioning; users can manually back up or use their own git.

### Design

The scratchpad directory becomes a git repository:

```
$MEMEX_HOME/scratchpad/
├── .git/                    # Auto-initialized on first write
├── preschool-search.md
└── career-thoughts.md
```

### Behavior

- **Auto-init**: First scratchpad write initializes git repo if not present
- **Auto-commit**: Every write/append/delete/move creates a commit
  - `Write preschool-search.md`
  - `Append to preschool-search.md`
  - `Delete old-notes.md`
  - `Move draft.md -> reading/book-notes.md`
- **No auto-push**: Local-only by default (user configures remote if desired)

### CLI Commands

```bash
mx scratchpad log [path]              # Show history (all or single file)
mx scratchpad show <path> <commit>    # Show file at specific commit
mx scratchpad restore <path> <commit> # Restore file to previous version
mx scratchpad diff <path>             # Show uncommitted changes
```

### Implementation Notes

```python
import subprocess

def _git_commit(root: Path, message: str) -> None:
    """Stage all changes and commit."""
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--allow-empty-message"],
        cwd=root,
        check=True,
        capture_output=True,  # Suppress output
    )

def _ensure_git_repo(root: Path) -> None:
    """Initialize git repo if not present."""
    git_dir = root / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initialize scratchpad"],
            cwd=root,
            check=True,
        )
```

### Agent Tools (v1)

```python
@agent.tool
async def scratchpad_history(ctx: RunContext[AgentDeps], path: str | None = None) -> str:
    """Show version history for scratchpad documents."""
    ...

@agent.tool
async def scratchpad_restore(ctx: RunContext[AgentDeps], path: str, commit: str) -> str:
    """Restore a document to a previous version."""
    ...
```

### Open Questions (v1)

1. **Commit frequency**: Every operation, or batch at session end?
2. **Remote sync**: Should we support `mx scratchpad push/pull`?
3. **Conflicts**: How to handle if user manually edits and creates conflicts?

## Markdown Validation

### Question: Should we lint markdown on write?

**Options**:

1. **No validation** - Accept any content, let the user/agent deal with malformed markdown
   - Pros: Simple, flexible, fast
   - Cons: Garbage in, garbage out

2. **Structural validation only** - Check frontmatter is valid YAML, basic markdown structure
   - Pros: Catches obvious errors without being restrictive
   - Cons: Partial solution

3. **Full linting with rumdl** - Use [rumdl](https://github.com/rvben/rumdl) for comprehensive markdown linting
   - Pros: Consistent, well-formed documents
   - Cons: Adds dependency, may reject valid-but-unconventional markdown

**Recommendation**: Start with **structural validation** (option 2) for MVP:
- Validate YAML frontmatter parses correctly
- Ensure document has reasonable structure (not binary garbage)
- Don't enforce style rules

Consider adding optional rumdl integration later if document quality becomes an issue. The agent is generating most content, and LLMs generally produce well-formed markdown.

### Implementation (Structural)

```python
def validate_content(content: str) -> None:
    """Basic structural validation before write."""
    # Check frontmatter if present
    if content.startswith("---"):
        match = _FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                yaml.safe_load(match.group(1))
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid frontmatter YAML: {e}")

    # Check for binary content (null bytes)
    if "\x00" in content:
        raise ValueError("Binary content not allowed in markdown documents")

    # Check reasonable size
    if len(content) > 1_000_000:  # 1MB
        raise ValueError("Document too large (max 1MB)")
```

## Migration

No migration needed—purely additive:
- Creates `$MEMEX_HOME/scratchpad/` on first use
- Existing Memex installations continue working

## Open Questions

1. **Max document size**: Should we limit document size? Large files could bloat context.
   - **Decision**: Warn if >50KB, truncate in context injection

2. ~~**Document deletion**: Should we support deleting documents?~~
   - **Decision**: Yes, added `Delete` operation. Agent confirms with user before deleting.

3. ~~**Rename/move**: Should we support renaming or moving documents?~~
   - **Decision**: Yes, added `Move` operation. Enables agent to reorganize.

4. **Conflict with database**: What if user says "note that Sarah likes coffee"?
   - **Decision**: Agent asks user for clarification when intent is ambiguous.
     Example: "Should I add this as a note on Sarah's record, or start a new scratchpad document?"

## Tasks

1. [x] Design document (this file)
2. [ ] Create `src/memex/scratchpad/__init__.py`
3. [ ] Create `src/memex/scratchpad/ops.py` with:
   - Pydantic models (Read, Write, Append, List, Search, Delete, Move)
   - Path validation
   - Frontmatter parsing/generation
   - Content validation
   - Executor function
4. [ ] Write tests in `tests/scratchpad/test_ops.py`
5. [ ] Register 7 tools in `agent.py` (read, write, append, list, search, delete, move)
6. [ ] Update `context.py` with scratchpad summary
7. [ ] Update system prompt with scratchpad vs database guidance
8. [ ] Add `scratchpad_root` to `AgentDeps`
9. [ ] Add `pyyaml` dependency to pyproject.toml
