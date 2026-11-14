import os

import pytest
from fastapi.testclient import TestClient

# Dummy values so config.mongo_uri() works; unit tests never contact Atlas.
# The E2E run opts out and loads the real .env instead.
if os.getenv("BDA_E2E") != "1":
    os.environ.setdefault("MONGODB_HOST", "example.mongodb.net")
    os.environ.setdefault("MONGODB_USERNAME", "test-user")
    os.environ.setdefault("MONGODB_PASSWORD", "p@ss word/with:chars")

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
