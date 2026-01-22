"""Tests for LLM response caching layer."""

import contextlib
import hashlib
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

from memex.cache import cached_llm, get_cache


class TestGetCache:
    """Tests for get_cache function."""

    def test_returns_none_when_env_var_unset(self) -> None:
        """Cache is disabled when MEMEX_CACHE_DIR is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is definitely not set
            os.environ.pop("MEMEX_CACHE_DIR", None)
            cache = get_cache()
            assert cache is None

    def test_returns_cache_when_env_var_set(self, tmp_path: Path) -> None:
        """Cache is enabled when MEMEX_CACHE_DIR is set."""
        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            cache = get_cache()
            assert cache is not None
            # Clean up
            cache.close()

    def test_creates_cache_directory(self, tmp_path: Path) -> None:
        """Cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            cache = get_cache()
            assert cache is not None
            assert cache_dir.exists()
            cache.close()


class TestCachedLlm:
    """Tests for cached_llm decorator."""

    def test_cache_miss_calls_function(self, tmp_path: Path) -> None:
        """Function is called on cache miss."""
        call_count = 0

        @cached_llm
        def expensive_call(prompt: str, _schema_hash: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result for {prompt}"

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            result = expensive_call("test prompt", "schema123")
            assert result == "result for test prompt"
            assert call_count == 1

    def test_cache_hit_returns_cached_value(self, tmp_path: Path) -> None:
        """Cached value is returned on cache hit."""
        call_count = 0

        @cached_llm
        def expensive_call(prompt: str, _schema_hash: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result for {prompt}"

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            # First call - cache miss
            result1 = expensive_call("test prompt", "schema123")
            # Second call - cache hit
            result2 = expensive_call("test prompt", "schema123")

            assert result1 == result2
            assert call_count == 1  # Function called only once

    def test_different_prompts_have_different_cache_entries(
        self, tmp_path: Path
    ) -> None:
        """Different prompts result in separate cache entries."""
        call_count = 0

        @cached_llm
        def expensive_call(prompt: str, _schema_hash: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result for {prompt}"

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            result1 = expensive_call("prompt A", "schema123")
            result2 = expensive_call("prompt B", "schema123")

            assert result1 == "result for prompt A"
            assert result2 == "result for prompt B"
            assert call_count == 2

    def test_schema_hash_change_invalidates_cache(self, tmp_path: Path) -> None:
        """Changing schema hash invalidates cache for same prompt."""
        call_count = 0

        @cached_llm
        def expensive_call(_prompt: str, _schema_hash: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result {call_count}"

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            result1 = expensive_call("test prompt", "schema_v1")
            result2 = expensive_call("test prompt", "schema_v2")

            # Both calls should execute because schema changed
            assert result1 == "result 1"
            assert result2 == "result 2"
            assert call_count == 2

    def test_disabled_cache_always_calls_function(self) -> None:
        """Function is always called when caching is disabled."""
        call_count = 0

        @cached_llm
        def expensive_call(_prompt: str, _schema_hash: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result {call_count}"

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MEMEX_CACHE_DIR", None)
            result1 = expensive_call("test prompt", "schema123")
            result2 = expensive_call("test prompt", "schema123")

            # Both calls should execute because caching is disabled
            assert result1 == "result 1"
            assert result2 == "result 2"
            assert call_count == 2

    def test_cache_key_format(self, tmp_path: Path) -> None:
        """Cache key follows schema_hash:prompt_hash format."""
        cache_dir = tmp_path / "cache"

        @cached_llm
        def expensive_call(_prompt: str, _schema_hash: str) -> str:
            return "result"

        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            expensive_call("my prompt", "my_schema")

            # Get the cache and check the key format
            cache = get_cache()
            assert cache is not None

            # Compute expected key
            prompt_hash = hashlib.sha256(b"my prompt").hexdigest()
            expected_key = f"my_schema:{prompt_hash}"

            assert expected_key in cache
            cache.close()

    def test_works_with_complex_return_types(self, tmp_path: Path) -> None:
        """Decorator handles complex return types correctly."""

        @cached_llm
        def expensive_call(prompt: str, schema_hash: str) -> dict[str, Any]:
            return {"response": prompt, "metadata": {"schema": schema_hash}}

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            result = expensive_call("test", "schema")
            assert result == {"response": "test", "metadata": {"schema": "schema"}}

            # Verify cached result matches
            cached_result = expensive_call("test", "schema")
            assert cached_result == result

    def test_cache_closed_even_when_function_raises(self, tmp_path: Path) -> None:
        """Cache is properly closed even when the wrapped function raises."""

        @cached_llm
        def failing_call(_prompt: str, _schema_hash: str) -> str:
            msg = "Simulated LLM failure"
            raise RuntimeError(msg)

        cache_dir = tmp_path / "cache"
        with patch.dict(os.environ, {"MEMEX_CACHE_DIR": str(cache_dir)}):
            # Call the function and expect it to raise
            with contextlib.suppress(RuntimeError):
                failing_call("test prompt", "schema123")

            # Verify the cache file isn't locked by opening a new cache connection
            # If the cache wasn't properly closed, this would fail or hang
            cache = get_cache()
            assert cache is not None

            # We should be able to write to the cache (proves it's not locked)
            cache["test_key"] = "test_value"
            assert cache["test_key"] == "test_value"
            cache.close()
