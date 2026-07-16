import pytest
from src.infrastructure.config import settings


@pytest.fixture(scope="session")
def test_settings():
    return settings
