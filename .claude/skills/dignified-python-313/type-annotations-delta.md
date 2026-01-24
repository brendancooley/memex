---
---

# Type Annotations - Python 3.13 Delta

This document contains type annotation features specific to Python 3.13.

For common type annotation guidance (Basic Collection Types, Union Types, Optional, Callable, etc.), see `type-annotations-common.md`.

## Overview

Python 3.13 continues the modern typing features from 3.10-3.12. All type features from previous versions continue to work.

**Note on PEP 649:** Deferred evaluation of annotations (PEP 649/749) is scheduled for Python 3.14, NOT 3.13. For forward references in Python 3.13, use `from __future__ import annotations`.

**Available from 3.12:**

- PEP 695 type parameter syntax: `def func[T](x: T) -> T`
- `type` statement for better type aliases

**Available from 3.11:**

- `Self` type for self-returning methods

**For forward references in 3.13:**

- Use `from __future__ import annotations` at the top of the file
- This enables deferred evaluation, allowing unquoted forward references
- Works well with static analysis tools (ruff, mypy, pyright)

## Self Type for Self-Returning Methods (3.11+)

✅ **PREFERRED** - Use Self for methods that return the instance:

```python
from typing import Self

class Builder:
    def set_name(self, name: str) -> Self:
        self.name = name
        return self

    def set_value(self, value: int) -> Self:
        self.value = value
        return self
```

## Generic Functions with PEP 695 (3.12+)

✅ **PREFERRED** - Use PEP 695 type parameter syntax:

```python
def first[T](items: list[T]) -> T | None:
    """Return first item or None if empty."""
    if not items:
        return None
    return items[0]

def identity[T](value: T) -> T:
    """Return value unchanged."""
    return value

# Multiple type parameters
def zip_dicts[K, V](keys: list[K], values: list[V]) -> dict[K, V]:
    """Create dict from separate key and value lists."""
    return dict(zip(keys, values))
```

🟡 **VALID** - TypeVar still works:

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    if not items:
        return None
    return items[0]
```

**Note**: Prefer PEP 695 syntax for simple generics. TypeVar is still needed for constraints/bounds.

## Generic Classes with PEP 695 (3.12+)

✅ **PREFERRED** - Use PEP 695 class syntax:

```python
class Stack[T]:
    """A generic stack data structure."""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> Self:
        self._items.append(item)
        return self

    def pop(self) -> T | None:
        if not self._items:
            return None
        return self._items.pop()

# Usage
int_stack = Stack[int]()
int_stack.push(42).push(43)
```

🟡 **VALID** - Generic with TypeVar still works:

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    # ... rest of implementation
```

**Note**: PEP 695 is cleaner - no imports needed, type parameter scope is local to class.

## Type Parameter Bounds (3.12+)

✅ **Use bounds with PEP 695**:

```python
class Comparable:
    def compare(self, other: object) -> int:
        ...

def max_value[T: Comparable](items: list[T]) -> T:
    """Get maximum value from comparable items."""
    return max(items, key=lambda x: x)
```

## Constrained TypeVars (Still Use TypeVar)

✅ **Use TypeVar for specific type constraints**:

```python
from typing import TypeVar

# Constrained to specific types - must use TypeVar
Numeric = TypeVar("Numeric", int, float)

def add(a: Numeric, b: Numeric) -> Numeric:
    return a + b
```

❌ **WRONG** - PEP 695 doesn't support constraints:

```python
# This doesn't constrain to int|float
def add[Numeric](a: Numeric, b: Numeric) -> Numeric:
    return a + b
```

## Type Aliases with type Statement (3.12+)

✅ **PREFERRED** - Use `type` statement:

```python
# Simple alias
type UserId = str
type Config = dict[str, str | int | bool]

# Generic type alias
type Result[T] = tuple[T, str | None]

def process(value: str) -> Result[int]:
    try:
        return (int(value), None)
    except ValueError as e:
        return (0, str(e))
```

🟡 **VALID** - Simple assignment still works:

```python
UserId = str  # Still valid
Config = dict[str, str | int | bool]  # Still valid
```

**Note**: `type` statement is more explicit and works better with generics.

## Forward References in Python 3.13

Python 3.13 does NOT have PEP 649 deferred evaluation yet (that's Python 3.14). For forward references, use `from __future__ import annotations`.

✅ **CORRECT** - Use future annotations for forward references:

```python
from __future__ import annotations

class Node:
    def __init__(self, value: int, parent: Node | None = None):
        self.value = value
        self.parent = parent

class Tree:
    def __init__(self) -> None:
        self.root: Node | None = None
```

✅ **CORRECT** - Validator methods returning self type:

```python
from __future__ import annotations

from pydantic import BaseModel, model_validator

class CreateTable(BaseModel):
    table: str
    columns: list[str]

    @model_validator(mode="after")
    def validate_columns(self) -> CreateTable:  # No quotes needed!
        if not self.columns:
            raise ValueError("Must have at least one column")
        return self
```

❌ **WRONG** - Quoted forward references (unnecessary with future annotations):

```python
from __future__ import annotations

class Node:
    # Don't use quotes when you have the future import
    def method(self) -> "Node":  # ❌ Unnecessary quotes
        ...
```

**Why use `from __future__ import annotations`:**

- Enables unquoted forward references
- Works with static analysis tools (ruff, mypy, pyright)
- Clean migration path to Python 3.14's native deferred evaluation
- No runtime overhead (annotations stored as strings)

## Complete Examples

### Tree Structure with Forward References

```python
from __future__ import annotations

from typing import Self
from collections.abc import Callable

class Node[T]:
    """Tree node with forward references."""

    def __init__(
        self,
        value: T,
        parent: Node[T] | None = None,
        children: list[Node[T]] | None = None,
    ) -> None:
        self.value = value
        self.parent = parent
        self.children = children or []

    def add_child(self, child: Node[T]) -> Self:
        """Add child and return self for chaining."""
        self.children.append(child)
        child.parent = self
        return self

    def find(self, predicate: Callable[[T], bool]) -> Node[T] | None:
        """Find first node matching predicate."""
        if predicate(self.value):
            return self

        for child in self.children:
            result = child.find(predicate)
            if result:
                return result

        return None

# Usage
root = Node[int](1)
root.add_child(Node[int](2)).add_child(Node[int](3))
```

### Generic Repository with PEP 695

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

class Entity[T]:
    """Base class for entities."""

    def __init__(self, id: T) -> None:
        self.id = id

class Repository[T](ABC):
    """Generic repository interface."""

    @abstractmethod
    def get(self, id: str) -> T | None:
        """Get entity by ID."""

    @abstractmethod
    def save(self, entity: T) -> None:
        """Save entity."""

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity, return True if deleted."""

class User(Entity[str]):
    def __init__(self, id: str, name: str) -> None:
        super().__init__(id)
        self.name = name

class UserRepository(Repository[User]):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def get(self, id: str) -> User | None:
        if id not in self._users:
            return None
        return self._users[id]

    def save(self, entity: User) -> None:
        self._users[entity.id] = entity

    def delete(self, id: str) -> bool:
        if id not in self._users:
            return False
        del self._users[id]
        return True
```

## Migration from 3.10/3.11 to 3.13

If migrating from Python 3.10/3.11:

1. **Keep `from __future__ import annotations`** - Still needed in 3.13 for forward refs
2. **Consider upgrading to PEP 695 syntax** - Cleaner generics (3.12+)
3. **Use `type` statement for aliases** - More explicit than assignment (3.12+)
4. **Remove quoted forward references** - Use future annotations instead

```python
# Python 3.10/3.11 (old style)
from __future__ import annotations
from typing import TypeVar, Generic

T = TypeVar("T")

class Node(Generic[T]):
    def __init__(self, value: T, parent: "Node[T] | None" = None):
        ...

# Python 3.13 (modernized)
from __future__ import annotations

from typing import Self

class Node[T]:
    def __init__(self, value: T, parent: Node[T] | None = None):
        ...
```

## Looking Ahead: Python 3.14

Python 3.14 will implement PEP 649/749 (Deferred Evaluation of Annotations). At that point:

- Forward references will work natively without `from __future__ import annotations`
- The future import will become unnecessary (but won't break anything)
- Annotations will be evaluated lazily by default

## What typing imports are still needed?

**Very rare:**

- `TypeVar` - Only for constrained/bounded type variables
- `Any` - Use sparingly when type truly unknown
- `Protocol` - Structural typing (prefer ABC)
- `TYPE_CHECKING` - Conditional imports to avoid circular dependencies

**Never needed:**

- `List`, `Dict`, `Set`, `Tuple` - Use built-in types
- `Union` - Use `|` operator
- `Optional` - Use `X | None`
- `Generic` - Use PEP 695 class syntax
