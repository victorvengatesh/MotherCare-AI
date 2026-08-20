"""Security regressions for authentication and request middleware."""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.core.middleware import _get_rate_limit_identity
from app.db import models
from app.db.database import Base, get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _request_with_token(token: str, ip: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/ai/chat",
            "raw_path": b"/ai/chat",
            "query_string": b"",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "client": (ip, 12345),
            "server": ("testserver", 80),
        }
    )


def test_public_registration_cannot_self_assign_admin(client, db_session):
    response = client.post(
        "/auth/register",
        data={
            "username": "public_user",
            "email": "public@example.com",
            "password": "strong-test-password",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    created = (
        db_session.query(models.User)
        .filter(models.User.username == "public_user")
        .one()
    )
    assert created.role == "patient"
    assert response.json()["data"]["role"] == "patient"


def test_forged_jwt_cannot_choose_rate_limit_identity(monkeypatch):
    real_secret = "a" * 32
    monkeypatch.setenv("MC_SECRET_KEY", real_secret)

    forged = jwt.encode(
        {"sub": "admin", "type": "access"},
        "b" * 32,
        algorithm="HS256",
    )

    identity = _get_rate_limit_identity(_request_with_token(forged))
    assert identity == "ip:127.0.0.1"


def test_valid_access_token_uses_verified_subject(monkeypatch):
    secret = "c" * 32
    monkeypatch.setenv("MC_SECRET_KEY", secret)

    token = jwt.encode(
        {"sub": "verified_user", "type": "access"},
        secret,
        algorithm="HS256",
    )

    identity = _get_rate_limit_identity(_request_with_token(token))
    assert identity == "user:verified_user"


def test_refresh_token_is_not_used_as_rate_limit_user_identity(monkeypatch):
    secret = "d" * 32
    monkeypatch.setenv("MC_SECRET_KEY", secret)

    token = jwt.encode(
        {"sub": "verified_user", "type": "refresh"},
        secret,
        algorithm="HS256",
    )

    identity = _get_rate_limit_identity(_request_with_token(token, ip="10.0.0.7"))
    assert identity == "ip:10.0.0.7"
