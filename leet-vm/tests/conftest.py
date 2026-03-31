import pytest

# configure pytest-asyncio to auto mode so all async tests run without decorator
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
