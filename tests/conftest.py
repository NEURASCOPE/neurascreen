"""Shared pytest configuration — auto-skip GUI tests when PySide6 is missing."""

import sys

import pytest

# Check PySide6 availability once
try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


def pytest_collection_modifyitems(config, items):
    """Skip test_gui_* tests when PySide6 is not installed."""
    if HAS_PYSIDE6:
        return

    skip_marker = pytest.mark.skip(reason="PySide6 not installed")
    for item in items:
        if "test_gui" in item.nodeid:
            item.add_marker(skip_marker)
