"""Fixtures comunes compartidas para la suite de tests en pytest."""

import pytest  # type: ignore
from fastapi.testclient import TestClient
from domain.repository import FakeCveRepository
from serve import create_app


@pytest.fixture
def client():
    """Application Factory fixture: entrega una instancia limpia con FakeCveRepository."""
    app = create_app(repo=FakeCveRepository())
    return TestClient(app)
