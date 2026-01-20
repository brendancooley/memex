"""Basic tests for memex package."""

from memex import __version__


def test_version() -> None:
    """Verify version is set."""
    assert __version__ == "0.1.0"
