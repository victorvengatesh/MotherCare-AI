import pytest
import asyncio
import time
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db import models
from app.services.auth_service import create_access_token, hash_password
from app.core.caching import RedisCache, SimpleCache
from app.services.email_service import send_email, _smtp_configured
from app.services.notification_service import create_notification
from app.services.appointment_service import update_appointment_status
from app.services.alert_service import create_maternal_alert

# SQLite Database for Testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase4_prod.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    # Force drop existing tables to clean any dirty state from crashed runs
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create seed users
        admin = models.User(
            id="admin-id", username="admin_user", email="admin@test.com",
            hashed_password=hash_password("adminpass"), role="admin"
        )
        doctor = models.User(
            id="doc-id", username="doctor1", email="doc@test.com",
            hashed_password=hash_password("docpass"), role="doctor"
        )
        patient = models.User(
            id="pat-id", username="patient1", email="pat@test.com",
            hashed_password=hash_password("patpass"), role="patient"
        )
        db.add_all([admin, doctor, patient])
        db.commit()

        # Create active assignment
        assign = models.DoctorPatientAssignment(
            id="assign-id", doctor_id="doc-id", patient_id="pat-id",
            status="active", assigned_by="admin_user"
        )
        db.add(assign)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def get_headers(username: str) -> dict:
    token = create_access_token(data={"sub": username, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


# ─── 1. DATABASE CONFIG & BOOLEAN COMPATIBILITY TESTS ────────────────────────

def test_database_postgresql_pooling():
    """Verify that PostgreSQL creates connection pool parameters correctly."""
    with patch("sqlalchemy.create_engine") as mock_create_engine:
        # Import dynamically to simulate module logic with environment variable set
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            from importlib import reload
            import app.db.database as db_mod
            reload(db_mod)
            
            # Assert create_engine was called with PostgreSQL pooling configurations
            mock_create_engine.assert_called_with(
                "postgresql://user:pass@host:5432/db",
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
    # Re-evaluate database module for normal sqlite environment
    from importlib import reload
    import app.db.database as db_mod
    reload(db_mod)

def test_database_boolean_coercion(test_db):
    """Verify boolean fields persist and retrieve correctly across queries."""
    notif = models.Notification(
        id="notif-1",
        user_id="pat-id",
        notif_type="follow_up",
        message="Standard test message",
        is_read=False
    )
    test_db.add(notif)
    test_db.commit()
    test_db.refresh(notif)

    # Assert retrieval gets Python boolean
    assert notif.is_read is False

    # Perform filter query
    unread = test_db.query(models.Notification).filter(models.Notification.is_read == False).all()
    assert len(unread) == 1
    assert unread[0].id == "notif-1"


# ─── 2. REDIS CACHING CIRCUIT BREAKER TESTS ───────────────────────────

def test_redis_cache_standard_operations():
    """Test standard cache operations when Redis is active."""
    cache = RedisCache("redis://localhost:6379/0", key_prefix="test_prefix")
    mock_client = MagicMock()
    cache._client = mock_client
    cache._available = True

    # Test set
    cache.set("key1", {"value": "cached_data"}, ttl=100)
    mock_client.setex.assert_called_once()
    
    # Test get
    mock_client.get.return_value = '{"value": "cached_data"}'
    res = cache.get("key1")
    assert res == {"value": "cached_data"}

    # Test delete
    cache.delete("key1")
    mock_client.delete.assert_called_with("test_prefix:key1")

def test_redis_cache_circuit_breaker():
    """Verify RedisCache trips its circuit breaker after consecutive failures."""
    cache = RedisCache("redis://localhost:6379/0", key_prefix="test_prefix")
    mock_client = MagicMock()
    # Mock exceptions on Redis operations
    mock_client.get.side_effect = Exception("Redis network error")
    mock_client.setex.side_effect = Exception("Redis network error")
    cache._client = mock_client
    cache._available = True
    cache._failed_attempts = 0
    cache._cooloff_period = 5.0 # Set short cool-off for test speed

    # Trigger consecutive failures
    cache.get("k") # Failure 1
    cache.set("k", "v") # Failure 2
    assert cache._available is True # Should still be online before threshold

    cache.get("k") # Failure 3 (Threshold hit)
    assert cache._available is False
    assert cache._failed_attempts == 3

    # Fast check: subsequent operations should IMMEDIATELY skip Redis and return None/No-op
    mock_client.reset_mock()
    res = cache.get("k")
    assert res is None
    mock_client.get.assert_not_called() # Redis connection bypassed

    # Verify recovery after cool-off expired
    cache._last_failure_time = time.time() - 6.0 # simulate 6s elapsed
    mock_client.ping.return_value = True # Successful reconnect ping
    
    # Reset GET side effect so it succeeds upon recovery
    mock_client.get.side_effect = None
    mock_client.get.return_value = None

    res = cache.get("k")
    assert cache._available is True
    assert cache._failed_attempts == 0
    mock_client.ping.assert_called_once()


# ─── 3. WEBSOCKET AUTHENTICATION & STABILITY TESTS ───────────────────────────

def test_websocket_authentication_invalid_token(client):
    """Ensure invalid JWT connections are rejected with WS policy violation."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/notifications?token=invalid_jwt") as ws:
            pass
    assert exc.value.code == 1008

def test_websocket_authentication_expired_token(client):
    """Ensure expired JWT connections are rejected."""
    expired_token = create_access_token(data={"sub": "patient1", "type": "access"}, expires_delta=timedelta(seconds=-10))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/notifications?token={expired_token}") as ws:
            pass
    assert exc.value.code == 1008

@patch("app.routes.ws._redis_subscriber")
def test_websocket_successful_connection_heartbeat(mock_sub, client):
    """Ensure valid connections remain active and heartbeats (pings) are sent."""
    async def mock_idle_sub(uid, ws):
        await asyncio.sleep(0.5)

    mock_sub.side_effect = mock_idle_sub
    token = create_access_token(data={"sub": "pat-id", "type": "access"})
    
    # Run with a short heartbeat interval for testing
    with patch("app.routes.ws.HEARTBEAT_INTERVAL", 0.1):
        with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
            # Receive immediate ping heartbeat
            msg = ws.receive_json()
            assert msg == {"type": "ping"}


# ─── 4. NOTIFICATION DELIVERY & WEBSOCKET BROADCAST TESTS ────────────────────

@patch("app.routes.ws._redis_subscriber")
def test_notification_websocket_broadcast(mock_sub, client, test_db):
    """Verify WebSocket forwards real-time notification messages."""
    
    # Mock redis subscriber to feed a live message
    async def mock_redis_flow(user_id, ws):
        from app.core.connection_manager import manager
        # Simulate receiving notification from Redis pub/sub
        payload = {
            "type": "notification",
            "data": {
                "id": "notif-id",
                "notif_type": "appointment",
                "message": "Live testing notification",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
        }
        await manager.send_to_user(user_id, payload)
        await asyncio.sleep(0.2) # Short sleep to avoid hanging the TestClient shutdown

    mock_sub.side_effect = mock_redis_flow
    token = create_access_token(data={"sub": "pat-id", "type": "access"})
    
    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "notification"
        assert msg["data"]["message"] == "Live testing notification"


# ─── 5. EMAIL NOTIFICATION DISPATCH & ROBUSTNESS TESTS ───────────────────────

@patch("aiosmtplib.send", new_callable=AsyncMock)
def test_email_smtp_dispatch_triggers(mock_send, test_db):
    """Ensure email notifications are dispatched on status updates and clinical alerts."""
    
    # Mock SMTP setup
    with patch.dict(os.environ, {"SMTP_HOST": "smtp.mail.com", "SMTP_USER": "test", "SMTP_PASS": "test"}):
        assert _smtp_configured() is True

        # Mock query setup
        appt = models.Appointment(
            id="appt-123",
            patient_id="pat-id",
            doctor_id="doc-id",
            appointment_datetime=datetime.utcnow() + timedelta(days=2),
            appointment_type="consultation",
            reason="Routine checkup",
            status="requested"
        )
        test_db.add(appt)
        test_db.commit()

        doctor = test_db.query(models.User).filter_by(id="doc-id").first()

        # 1. Test appointment status change email dispatch
        update_appointment_status(
            db=test_db,
            appt=appt,
            new_status="confirmed",
            actor=doctor
        )
        
        # Verify SMTP send is triggered asynchronously (wait a moment for tasks)
        time.sleep(0.1)
        mock_send.assert_called_once()
        assert "Confirmed" in mock_send.call_args[0][0]["Subject"]

        # 2. Test High Risk alert email dispatch
        mock_send.reset_mock()
        create_maternal_alert(
            db=test_db,
            patient_id="pat-id",
            risk_level="High",
            alert_source="test_system",
            warning_signs="Persistent severe headache"
        )
        time.sleep(0.1)
        mock_send.assert_called_once()
        assert "High Risk Alert" in mock_send.call_args[0][0]["Subject"]

@patch("aiosmtplib.send", new_callable=AsyncMock)
def test_email_smtp_failure_non_blocking(mock_send, test_db):
    """Ensure SMTP connection exceptions are caught and never crash the main transaction."""
    # Force SMTP error
    mock_send.side_effect = Exception("SMTP connection refused")

    with patch.dict(os.environ, {"SMTP_HOST": "smtp.mail.com", "SMTP_USER": "test", "SMTP_PASS": "test"}):
        appt = models.Appointment(
            id="appt-456",
            patient_id="pat-id",
            doctor_id="doc-id",
            appointment_datetime=datetime.utcnow() + timedelta(days=2),
            appointment_type="consultation",
            reason="Routine checkup",
            status="requested"
        )
        test_db.add(appt)
        test_db.commit()

        doctor = test_db.query(models.User).filter_by(id="doc-id").first()

        # Update status — should run completely without throwing an exception
        updated = update_appointment_status(
            db=test_db,
            appt=appt,
            new_status="cancelled",
            actor=doctor,
            reason="Doctor vacation"
        )
        
        time.sleep(0.1)
        # Verify status updated despite SMTP failure
        assert updated.status == "cancelled"
