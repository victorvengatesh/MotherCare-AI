import logging
import time
import concurrent.futures

logger = logging.getLogger("ai-wrapper")

# Import the production-grade circuit breaker from core
from app.core.circuit_breaker import gemini_circuit_breaker

def call_ai_with_retry(
    client, 
    model: str, 
    contents: str, 
    agent_name: str = "general",
    max_retries: int = 2,
    timeout: float = 10.0,
    fallback_text: str = "I am currently experiencing high load. Please try again in a few moments."
) -> str:
    """
    Global wrapper for all AI calls to Gemini with production-grade Circuit Breaker.
    
    Uses the global gemini_circuit_breaker instance from app.core.circuit_breaker.
    Circuit breaker handles:
      - State management (CLOSED → OPEN → HALF_OPEN)
      - Failure threshold tracking
      - Automatic recovery timeout
      - Thread-safe state transitions
    
    Args:
        client: google.genai.Client instance
        model: Model name (e.g., "gemini-2.5-flash")
        contents: Prompt/contents to send
        agent_name: Agent name for logging
        max_retries: Exponential backoff retry count
        timeout: Per-call timeout in seconds
        fallback_text: Fallback response when circuit is open or call fails
    
    Returns:
        Response text or fallback text
    """
    if client is None:
        logger.warning("AI service unavailable (client is None).", extra={"agent": agent_name})
        return fallback_text

    def _sync_call():
        """Internal function that makes the actual Gemini API call."""
        return client.models.generate_content(model=model, contents=contents)

    def _execute_with_timeout():
        """Execute the API call with timeout protection."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_sync_call)
            resp = future.result(timeout=timeout)
            
            if resp and hasattr(resp, "text") and resp.text:
                text = resp.text.strip()
                if text:
                    return text
                    
            raise ValueError("Empty or null response received from Gemini API.")

    # Use circuit breaker to wrap the call with state management
    def _call_with_retry():
        for attempt in range(max_retries):
            try:
                return _execute_with_timeout()
            except concurrent.futures.TimeoutError:
                logger.error(
                    "AI generation timeout",
                    extra={"attempt": attempt + 1, "agent": agent_name, "error_type": "TimeoutError"}
                )
            except Exception as e:
                logger.error(
                    "AI generation failure",
                    extra={"attempt": attempt + 1, "agent": agent_name, "error_type": type(e).__name__, "error": str(e)}
                )
            
            if attempt < max_retries - 1:
                backoff_time = 2 ** attempt
                logger.info(f"Retrying after {backoff_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(backoff_time)
        
        # All retries exhausted
        raise RuntimeError(f"AI service failed after {max_retries} attempts")

    # Circuit breaker wraps the entire retry logic
    result = gemini_circuit_breaker.call(_call_with_retry)
    
    # If circuit breaker returned a fallback dict, extract the response
    if isinstance(result, dict) and "response" in result:
        return result.get("response", fallback_text)
    
    # If circuit breaker returned a string, return it
    if isinstance(result, str):
        return result
    
    # Shouldn't reach here, but safety fallback
    logger.warning("Unexpected result type from circuit breaker, returning fallback")
    return fallback_text
