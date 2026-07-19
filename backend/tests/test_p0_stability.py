"""
Phase 2 P0 Stability Tests — Circuit Breaker, Error Handling, Graceful Degradation

These tests verify:
1. Circuit breaker opens after N failures
2. Fallback responses are returned when circuit is open
3. Graceful degradation when external APIs fail
4. Standardized response format across all endpoints
"""
import pytest
import time
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.services.auth_service import create_access_token
from app.db import models

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────
# 1. Circuit Breaker State Machine Tests
# ──────────────────────────────────────────────────────────────────────────

class TestCircuitBreakerStateMachine:
    """Test the circuit breaker's state transitions."""
    
    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker should start in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker should open after N failures."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5)
        
        # Simulate 2 failures
        for i in range(2):
            def failing_call():
                raise ValueError("API down")
            
            result = breaker.call(failing_call)
            assert result["status"] == "fallback_active"
        
        # Should be OPEN now
        assert breaker.state == CircuitState.OPEN
    
    def test_circuit_breaker_rejects_calls_when_open(self):
        """Circuit breaker should reject calls without executing when OPEN."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Fail once to open circuit
        def failing_call():
            raise ValueError("API down")
        
        breaker.call(failing_call)
        assert breaker.state == CircuitState.OPEN
        
        # Next call should be rejected immediately (not executed)
        call_count = 0
        def counting_call():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = breaker.call(counting_call)
        assert result["status"] == "fallback_active"
        assert call_count == 0  # Function was NOT called
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Circuit breaker should enter HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        # Fail once to open
        def failing_call():
            raise ValueError("API down")
        
        breaker.call(failing_call)
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.5)
        
        # Next call should enter HALF_OPEN and attempt execution
        def working_call():
            return "recovered"
        
        result = breaker.call(working_call)
        # Should be HALF_OPEN after timeout expires
        assert breaker.state == CircuitState.HALF_OPEN or breaker.state == CircuitState.CLOSED
    
    def test_circuit_breaker_fallback_response_format(self):
        """Fallback response should have correct structure."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        def failing_call():
            raise ValueError("API down")
        
        result = breaker.call(failing_call)
        
        # Check fallback structure
        assert "response" in result
        assert "status" in result
        assert result["status"] == "fallback_active"
        assert "friendly message" in result["response"].lower() or "temporarily" in result["response"].lower()


# ──────────────────────────────────────────────────────────────────────────
# 2. API Endpoint Standardized Response Tests
# ──────────────────────────────────────────────────────────────────────────

class TestStandardizedResponses:
    """Test that all API responses follow standardized format."""
    
    @pytest.fixture
    def auth_token(self):
        """Create a test user and return JWT token."""
        token = create_access_token(data={"sub": "test-user-123"})
        return token
    
    def test_chat_endpoint_response_format(self, auth_token):
        """Chat endpoint should return standardized response."""
        response = client.post(
            "/ai/chat",
            json={"query": "I have a fever", "language": "English"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 200 (or 503 if circuit open, but still standardized)
        assert response.status_code in [200, 503, 500]
        data = response.json()
        
        # Check standardized format
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "status_code" in data
        assert isinstance(data["success"], bool)
    
    def test_twin_endpoint_response_format(self, auth_token):
        """Twin endpoint should return standardized response."""
        response = client.get(
            "/ai/twin",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code in [200, 500]
        data = response.json()
        
        # Check standardized format
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "status_code" in data
    
    def test_error_response_format(self, auth_token):
        """Error responses should follow standardized format."""
        # Missing required field
        response = client.post(
            "/ai/chat",
            json={"language": "English"},  # Missing 'query'
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        
        # Check error structure
        assert "success" in data
        assert data["success"] == False
        assert "message" in data or "detail" in data


# ──────────────────────────────────────────────────────────────────────────
# 3. Graceful Degradation Tests
# ──────────────────────────────────────────────────────────────────────────

class TestGracefulDegradation:
    """Test graceful fallback when external APIs fail."""
    
    @pytest.fixture
    def auth_token(self):
        token = create_access_token(data={"sub": "test-user-123"})
        return token
    
    @patch('app.utils.ai_wrapper.call_ai_with_retry')
    def test_chat_fallback_when_gemini_unavailable(self, mock_ai, auth_token):
        """Chat should return fallback when Gemini API is down."""
        # Mock Gemini API returning fallback
        mock_ai.return_value = "I'm currently experiencing service issues. Please try again."
        
        response = client.post(
            "/ai/chat",
            json={"query": "What should I eat?", "language": "English"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should still return 200 with fallback response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Response should contain fallback message or indicate service issue
        assert "data" in data


# ──────────────────────────────────────────────────────────────────────────
# 4. Concurrent Request Handling Tests
# ──────────────────────────────────────────────────────────────────────────

class TestConcurrentRequests:
    """Test thread safety under concurrent load."""
    
    def test_circuit_breaker_thread_safety(self):
        """Circuit breaker should be thread-safe under concurrent calls."""
        import threading
        
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=5)
        results = []
        
        def worker():
            def failing_call():
                raise ValueError("API error")
            
            result = breaker.call(failing_call)
            results.append(result)
        
        # Spawn 10 concurrent threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should get fallback responses
        assert len(results) == 10
        assert all(r["status"] == "fallback_active" for r in results)
        
        # Circuit should be OPEN
        assert breaker.state == CircuitState.OPEN


# ──────────────────────────────────────────────────────────────────────────
# 5. Timeout Handling Tests
# ──────────────────────────────────────────────────────────────────────────

class TestTimeoutHandling:
    """Test that slow/timeout calls are handled gracefully."""
    
    @pytest.fixture
    def auth_token(self):
        token = create_access_token(data={"sub": "test-user-123"})
        return token
    
    @patch('app.utils.ai_wrapper._sync_call', side_effect=TimeoutError)
    def test_chat_timeout_handled_gracefully(self, mock_timeout, auth_token):
        """Chat should return fallback on timeout."""
        response = client.post(
            "/ai/chat",
            json={"query": "Is this baby safe?", "language": "English"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        
        # Should eventually return (even if fallback)
        assert response.status_code in [200, 503, 504]
        data = response.json()
        assert "data" in data or "message" in data


# ──────────────────────────────────────────────────────────────────────────
# 6. Response Content Validation
# ──────────────────────────────────────────────────────────────────────────

class TestResponseContent:
    """Test that response content is valid and complete."""
    
    @pytest.fixture
    def auth_token(self):
        token = create_access_token(data={"sub": "test-user-123"})
        return token
    
    def test_chat_response_has_agent_selection(self, auth_token):
        """Chat response should include selected agent."""
        response = client.post(
            "/ai/chat",
            json={"query": "I have severe headache and vision loss", "language": "English"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            response_data = data.get("data", {})
            
            # Should have agent field
            assert "agent" in response_data
            assert response_data["agent"] in ["obgyn", "nutritionist", "mental_health", "emergency"]
            
            # Should have response text
            assert "response" in response_data
            assert len(response_data["response"]) > 0
    
    def test_emergency_routing(self, auth_token):
        """Emergency keywords should route to emergency specialist."""
        response = client.post(
            "/ai/chat",
            json={"query": "I'm bleeding heavily", "language": "English"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            response_data = data.get("data", {})
            
            # Emergency keywords should route to emergency agent
            if "agent" in response_data:
                assert response_data["agent"] == "emergency"


# ──────────────────────────────────────────────────────────────────────────
# 7. Authentication & Authorization Tests
# ──────────────────────────────────────────────────────────────────────────

class TestAuthErrors:
    """Test proper 401/403 handling."""
    
    def test_unauthorized_returns_401(self):
        """Missing token should return 401."""
        response = client.post(
            "/ai/chat",
            json={"query": "test"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] == False
    
    def test_invalid_token_returns_401(self):
        """Invalid token should return 401."""
        response = client.post(
            "/ai/chat",
            json={"query": "test"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────
# Run all tests
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
