"""LLM response caching layer.

Optional caching for LLM calls, controlled via MEMEX_CACHE_DIR env var.
Uses diskcache (SQLite-backed) for persistent, inspectable caching.

Use cases:
- Local dev iteration (avoid re-calling LLM while tweaking post-processing)
- Test runs (deterministic, fast, no API cost after first run)
- NOT for production
"""

import hashlib
import os
from collections.abc import Callable
from functools import wraps

from diskcache import Cache


def get_cache() -> Cache | None:
    """Return a Cache instance if MEMEX_CACHE_DIR is set, otherwise None.

    The cache directory is created automatically if it doesn't exist.
    """
    cache_dir = os.environ.get("MEMEX_CACHE_DIR")
    if cache_dir:
        return Cache(cache_dir)
    return None


def cached_llm[T](func: Callable[[str, str], T]) -> Callable[[str, str], T]:
    """Decorator for caching LLM calls.

    Expects decorated function to have signature:
        func(prompt: str, schema_hash: str) -> T

    Cache key format: schema_hash:prompt_hash

    When MEMEX_CACHE_DIR is unset, caching is disabled and the function
    is called directly.

    Args:
        func: Function to wrap. Must accept (prompt, schema_hash) parameters.

    Returns:
        Wrapped function with caching behavior.
    """

    @wraps(func)
    def wrapper(prompt: str, schema_hash: str) -> T:
        cache = get_cache()

        if cache is None:
            # Caching disabled, call function directly
            return func(prompt, schema_hash)

        # Build cache key: schema_hash:prompt_hash
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache_key = f"{schema_hash}:{prompt_hash}"

        # Use context manager to ensure cache is closed even if func raises
        with cache:
            # Check cache first (LBYL)
            if cache_key in cache:
                return cache[cache_key]

            # Cache miss - call function and store result
            result = func(prompt, schema_hash)
            cache[cache_key] = result
            return result

    return wrapper
