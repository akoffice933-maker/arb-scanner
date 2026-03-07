"""
Pytest configuration and fixtures.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_event_loop():
    """Setup event loop for async tests."""
    pass


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)
