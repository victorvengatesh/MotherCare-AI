import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import get_current_user
from app.db import models

def mock_get_current_user():
    return models.User(id="test_user", username="test")

@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_analyze_no_symptoms(client):
    response = client.post("/analyze", data={"symptoms": ""})
    assert response.status_code in (400, 422)

def test_analyze_invalid_file_extension(client):
    pass
