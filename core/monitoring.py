# -*- coding: utf-8 -*-
"""
Advanced monitoring, resilience, and circuit breaker patterns.
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Any, Dict, List, Optional
from enum import Enum
from functools import wraps
import logging

from core.logging import get_logger

logger = get_logger("monitoring")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascading failures by failing fast.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = threading.Lock()
        
        logger.info(f"CircuitBreaker initialized: threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("CircuitBreaker entering HALF_OPEN state")
                else:
                    raise Exception(f"CircuitBreaker is OPEN (failures: {self.failure_count})")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has passed."""
        if self.last_failure_time is None:
            return True
        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("CircuitBreaker RECOVERED - back to CLOSED")
            self.success_count += 1
    
    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker OPENED after {self.failure_count} failures"
                )
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED


class RateLimiter:
    """
    Token bucket rate limiter.
    Prevents overwhelming downstream services.
    """
    
    def __init__(self, max_calls: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in window
            window_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
        self._lock = threading.Lock()
        
        logger.info(f"RateLimiter initialized: {max_calls} calls per {window_seconds}s")
    
    def allow(self) -> bool:
        """Check if call is allowed."""
        with self._lock:
            now = time.time()
            # Remove expired calls
            self.calls = [
                call_time for call_time in self.calls
                if now - call_time < self.window_seconds
            ]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            logger.warning(
                f"RateLimit exceeded: {len(self.calls)}/{self.max_calls} in window"
            )
            return False
    
    def wait_if_needed(self) -> float:
        """Wait until a call is allowed, return wait time."""
        with self._lock:
            now = time.time()
            self.calls = [
                call_time for call_time in self.calls
                if now - call_time < self.window_seconds
            ]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return 0.0
            
            # Wait for oldest call to expire
            oldest_call = min(self.calls)
            wait_time = self.window_seconds - (now - oldest_call) + 0.1
            logger.info(f"RateLimiter: waiting {wait_time:.2f}s")
            
            time.sleep(wait_time)
            self.calls.append(time.time())
            return wait_time


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""
    pass


def timeout_seconds(seconds: float) -> Callable:
    """
    Decorator to add timeout to function.
    
    Args:
        seconds: Timeout in seconds
    
    Raises:
        TimeoutError: If function takes longer than timeout
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import signal
            
            def handle_timeout(signum, frame):
                raise TimeoutError(f"{func.__name__} exceeded {seconds}s timeout")
            
            # Set signal handler (Unix only)
            try:
                signal.signal(signal.SIGALRM, handle_timeout)
                signal.alarm(int(seconds))
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.alarm(0)
            except AttributeError:
                # Windows doesn't support signal.alarm, use simpler approach
                logger.warning("Timeout decorator not fully supported on this OS")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def max_iterations(max_count: int = 100) -> Callable:
    """
    Decorator to limit function iterations.
    Prevents infinite loops.
    
    Args:
        max_count: Maximum iterations allowed
    
    Raises:
        RuntimeError: If iterations exceed limit
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Store iteration count in function attribute
            if not hasattr(wrapper, '_iteration_count'):
                wrapper._iteration_count = {}
            
            import threading
            thread_id = threading.get_ident()
            
            wrapper._iteration_count[thread_id] = wrapper._iteration_count.get(thread_id, 0) + 1
            
            if wrapper._iteration_count[thread_id] > max_count:
                logger.error(f"{func.__name__} exceeded {max_count} iterations")
                raise RuntimeError(
                    f"{func.__name__} exceeded maximum iterations ({max_count})"
                )
            
            try:
                return func(*args, **kwargs)
            finally:
                wrapper._iteration_count[thread_id] -= 1
                if wrapper._iteration_count[thread_id] == 0:
                    del wrapper._iteration_count[thread_id]
        
        return wrapper
    return decorator


class SystemMonitor:
    """
    Monitor system health and performance metrics.
    """
    
    def __init__(self):
        """Initialize system monitor."""
        self.start_time = datetime.now()
        self.total_requests = 0
        self.total_errors = 0
        self.total_retries = 0
        self.requests_by_type = {}
        self.errors_by_type = {}
        self.response_times = []
        self._lock = threading.Lock()
        
        logger.info("SystemMonitor initialized")
    
    def record_request(self, request_type: str, response_time: float = 0.0):
        """Record successful request."""
        with self._lock:
            self.total_requests += 1
            self.requests_by_type[request_type] = self.requests_by_type.get(request_type, 0) + 1
            if response_time > 0:
                self.response_times.append(response_time)
    
    def record_error(self, error_type: str, error_msg: str = ""):
        """Record error."""
        with self._lock:
            self.total_errors += 1
            self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
            logger.error(f"Error recorded: {error_type} - {error_msg}")
    
    def record_retry(self, operation: str, attempt: int = 1):
        """Record retry event."""
        with self._lock:
            self.total_retries += 1
            logger.warning(f"Retry recorded: {operation} (attempt {attempt})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self._lock:
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            avg_response_time = (
                sum(self.response_times) / len(self.response_times)
                if self.response_times else 0
            )
            
            error_rate = (
                self.total_errors / self.total_requests * 100
                if self.total_requests > 0 else 0
            )
            
            return {
                'uptime_seconds': uptime,
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'total_retries': self.total_retries,
                'error_rate_percent': error_rate,
                'avg_response_time': avg_response_time,
                'requests_by_type': dict(self.requests_by_type),
                'errors_by_type': dict(self.errors_by_type),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_health_check(self) -> Dict[str, Any]:
        """Get health status."""
        stats = self.get_stats()
        
        # Simple health criteria
        error_rate = stats['error_rate_percent']
        is_healthy = error_rate < 5.0 and stats['total_requests'] > 0
        
        return {
            'healthy': is_healthy,
            'error_rate_percent': error_rate,
            'total_errors': stats['total_errors'],
            'total_requests': stats['total_requests'],
            'status': 'HEALTHY' if is_healthy else 'DEGRADED' if error_rate < 10 else 'UNHEALTHY',
            'timestamp': datetime.now().isoformat()
        }


# Global monitor instance
_system_monitor = None


def get_system_monitor() -> SystemMonitor:
    """Get or create global system monitor."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor
