import io

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.db import models
from app.main import app
from app.routes.analyze import validate_file
from app.services.auth_service import get_current_user


def mock_get_current_user():
    return models.User(id="test_user", username="test", role="patient")


@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_analyze_no_symptoms(client):
    response = client.post("/analyze", data={"symptoms": ""})
    assert response.status_code in (400, 422)


def test_validate_file_rejects_invalid_extension():
    upload = UploadFile(filename="malicious.exe", file=io.BytesIO(b"not-an-image"))

    with pytest.raises(Exception) as exc_info:
        validate_file(upload)

    exc = exc_info.value
    assert getattr(exc, "status_code", None) == 400
    assert "Unsupported file type" in getattr(exc, "detail", "")


def test_validate_file_accepts_supported_extension():
    upload = UploadFile(filename="scan.png", file=io.BytesIO(b"placeholder"))
    assert validate_file(upload) is None
