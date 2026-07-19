"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by monitoring external API calls (Gemini).
States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery) → CLOSED
"""
import time
import logging
import threading
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "CLOSED"           # Normal operation, requests go through
    OPEN = "OPEN"               # API failing, requests short-circuit to fallback
    HALF_OPEN = "HALF_OPEN"     # Testing if API has recovered


class CircuitBreaker:
    """
    Thread-safe circuit breaker for external API calls.
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        result = breaker.call(risky_api_call, arg1, arg2, key=value)
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying to recover (HALF_OPEN)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        If circuit is OPEN, returns fallback without calling func.
        """
        with self._lock:
            # Check if we should attempt recovery
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("CircuitBreaker entering HALF_OPEN — testing recovery")
                else:
                    logger.warning("CircuitBreaker is OPEN — short-circuiting request")
                    return self._fallback_response()

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            return self._fallback_response()

    def _on_success(self):
        """Called when a call succeeds."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            self.last_failure_time = None
            logger.info("CircuitBreaker reset to CLOSED — API recovered")

    def _on_failure(self, error: Exception):
        """Called when a call fails."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.error(f"CircuitBreaker failure {self.failure_count}/{self.failure_threshold}: {str(error)}")

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.critical(f"CircuitBreaker OPENED after {self.failure_count} failures!")

    def _fallback_response(self) -> dict:
        """Return a safe fallback response when circuit is open."""
        return {
            "response": "I'm currently experiencing high load or a temporary connection issue. Please try again in a moment while I reconnect to my medical knowledge base.",
            "status": "fallback_active",
            "agent": "system",
            "rag_context_used": False,
            "language": "English",
        }

    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open."""
        with self._lock:
            return self.state == CircuitState.OPEN

    @property
    def current_state(self) -> str:
        """Get current state as string."""
        with self._lock:
            return self.state.value


# Global instances for each critical service
gemini_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
rag_circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30)
