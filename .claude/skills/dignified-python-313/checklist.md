---
---

- **Use** `from __future__ import annotations` for files with forward references
- **Always** use modern type syntax: `list[str]`, `str | None`
- **Prefer** PEP 695 generics: `class Stack[T]:` instead of `Generic[T]`
- **Remove** quoted forward refs when using future annotations: `-> MyClass` not `-> "MyClass"`
