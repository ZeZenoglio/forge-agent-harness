import pytest

from backend.agent.fake_runtime import FakeRuntime


@pytest.fixture
def fake_runtime() -> FakeRuntime:
    """Provides a fresh FakeRuntime instance for unit tests."""
    return FakeRuntime()
