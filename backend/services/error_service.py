"""
Centralized error tracking and handling service.

Provides error classification, grouping, notification routing,
and circuit breaker patterns for external services.
"""
import time
from typing import Dict, Optional, Tuple, List
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from backend.core.sentry_config import capture_exception, capture_message


class ErrorClassification(str, Enum):
    """Error classification types."""
    TRANSIENT = "transient"  # Temporary errors that may succeed on retry
    PERMANENT = "permanent"  # Errors that won't succeed on retry
    USER_ERROR = "user_error"  # User input errors
    UNKNOWN = "unknown"  # Unclassified errors


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Too many failures, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ErrorService:
    """
    Centralized error handling service.
    
    Features:
    - Error classification
    - Error grouping and aggregation
    - Rate calculation
    - Notification routing
    - Circuit breaker pattern
    """
    
    def __init__(self):
        """Initialize error service."""
        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_timestamps: Dict[str, List[float]] = defaultdict(list)
        self.last_notification: Dict[str, float] = {}
        
        # Circuit breakers
        self.circuit_states: Dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self.circuit_failures: Dict[str, int] = defaultdict(int)
        self.circuit_last_failure: Dict[str, float] = {}
        
        # Configuration
        self.notification_cooldown = 300  # 5 minutes
        self.error_rate_window = 300  # 5 minutes
        self.circuit_failure_threshold = 5
        self.circuit_timeout = 60  # 1 minute
        self.circuit_half_open_max_requests = 3
        self.circuit_half_open_requests: Dict[str, int] = defaultdict(int)
    
    def classify_error(self, error: Exception) -> ErrorClassification:
        """
        Classify an error by type.
        
        Args:
            error: Exception to classify
        
        Returns:
            Error classification
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Transient errors (network, timeout, rate limit)
        transient_indicators = [
            'timeout',
            'connection',
            'network',
            'rate limit',
            'too many requests',
            'service unavailable',
            'bad gateway',
            'gateway timeout',
        ]
        
        if any(ind in error_msg for ind in transient_indicators):
            return ErrorClassification.TRANSIENT
        
        # User errors (validation, not found, forbidden)
        user_error_types = [
            'ValidationError',
            'ValueError',
            'KeyError',
            'NotFoundError',
            'ForbiddenError',
            'UnauthorizedError',
        ]
        
        if error_type in user_error_types:
            return ErrorClassification.USER_ERROR
        
        # Permanent errors (programming errors, config errors)
        permanent_indicators = [
            'not implemented',
            'attribute error',
            'type error',
            'import error',
            'syntax error',
        ]
        
        if any(ind in error_msg for ind in permanent_indicators):
            return ErrorClassification.PERMANENT
        
        return ErrorClassification.UNKNOWN
    
    def classify_severity(
        self,
        error: Exception,
        classification: ErrorClassification,
    ) -> ErrorSeverity:
        """
        Determine error severity.
        
        Args:
            error: Exception
            classification: Error classification
        
        Returns:
            Error severity
        """
        # User errors are typically warnings
        if classification == ErrorClassification.USER_ERROR:
            return ErrorSeverity.WARNING
        
        # Database errors are critical
        if 'database' in str(error).lower() or 'sql' in str(error).lower():
            return ErrorSeverity.CRITICAL
        
        # Permanent errors are errors
        if classification == ErrorClassification.PERMANENT:
            return ErrorSeverity.ERROR
        
        # Transient errors are warnings
        if classification == ErrorClassification.TRANSIENT:
            return ErrorSeverity.WARNING
        
        return ErrorSeverity.ERROR
    
    def group_error(self, error: Exception, endpoint: str) -> str:
        """
        Generate error grouping key.
        
        Args:
            error: Exception
            endpoint: API endpoint where error occurred
        
        Returns:
            Grouping key for aggregation
        """
        error_type = type(error).__name__
        return f"{endpoint}:{error_type}"
    
    async def track_error(
        self,
        error: Exception,
        endpoint: str,
        method: str = "GET",
        tenant_id: Optional[str] = None,
        notify: bool = True,
    ) -> Tuple[ErrorClassification, ErrorSeverity]:
        """
        Track an error occurrence.
        
        Args:
            error: Exception that occurred
            endpoint: API endpoint
            method: HTTP method
            tenant_id: Optional tenant identifier
            notify: Whether to send notifications
        
        Returns:
            Tuple of (classification, severity)
        """
        # Classify error
        classification = self.classify_error(error)
        severity = self.classify_severity(error, classification)
        
        # Group error
        group_key = self.group_error(error, endpoint)
        
        # Track count and timestamp
        now = time.time()
        self.error_counts[group_key] += 1
        self.error_timestamps[group_key].append(now)
        
        # Clean old timestamps (outside the rate window)
        cutoff = now - self.error_rate_window
        self.error_timestamps[group_key] = [
            ts for ts in self.error_timestamps[group_key]
            if ts > cutoff
        ]
        
        # Send to Sentry
        capture_exception(error)
        
        # Route notification if needed
        if notify:
            await self._route_notification(
                error=error,
                classification=classification,
                severity=severity,
                group_key=group_key,
                endpoint=endpoint,
                method=method,
                tenant_id=tenant_id,
            )
        
        return classification, severity
    
    async def _route_notification(
        self,
        error: Exception,
        classification: ErrorClassification,
        severity: ErrorSeverity,
        group_key: str,
        endpoint: str,
        method: str,
        tenant_id: Optional[str],
    ):
        """
        Route error notification based on severity.
        
        Args:
            error: Exception
            classification: Error classification
            severity: Error severity
            group_key: Error grouping key
            endpoint: API endpoint
            method: HTTP method
            tenant_id: Optional tenant ID
        """
        now = time.time()
        
        # Check cooldown to avoid spam
        last_notification = self.last_notification.get(group_key, 0)
        if now - last_notification < self.notification_cooldown:
            return  # Skip notification during cooldown
        
        # Calculate error rate
        error_rate = self.calculate_error_rate(group_key)
        
        # Determine if we should notify
        should_notify = False
        notification_type = "batch"
        
        if severity == ErrorSeverity.CRITICAL:
            should_notify = True
            notification_type = "immediate"
        elif severity == ErrorSeverity.ERROR and error_rate > 0.1:
            should_notify = True
            notification_type = "immediate"
        elif error_rate > 0.05:  # 5% error rate
            should_notify = True
            notification_type = "batch"
        
        if should_notify:
            await self._send_notification(
                error=error,
                classification=classification,
                severity=severity,
                error_rate=error_rate,
                endpoint=endpoint,
                method=method,
                tenant_id=tenant_id,
                notification_type=notification_type,
            )
            
            # Update last notification time
            self.last_notification[group_key] = now
    
    async def _send_notification(
        self,
        error: Exception,
        classification: ErrorClassification,
        severity: ErrorSeverity,
        error_rate: float,
        endpoint: str,
        method: str,
        tenant_id: Optional[str],
        notification_type: str,
    ):
        """
        Send error notification.
        
        In a real implementation, this would send to:
        - Slack webhook
        - Email
        - PagerDuty
        
        For now, we just log and send to Sentry.
        """
        message = (
            f"Error Alert ({severity.value.upper()})\n"
            f"Endpoint: {method} {endpoint}\n"
            f"Type: {type(error).__name__}\n"
            f"Classification: {classification.value}\n"
            f"Error Rate: {error_rate * 100:.2f}%\n"
            f"Message: {str(error)}"
        )
        
        if tenant_id:
            message += f"\nTenant: {tenant_id}"
        
        print(f"📢 {message}")
        
        # Send to Sentry as a message
        capture_message(
            message,
            level=severity.value,
            tags={
                "endpoint": endpoint,
                "method": method,
                "classification": classification.value,
                "notification_type": notification_type,
            }
        )
    
    def calculate_error_rate(self, group_key: str, window_seconds: int = 300) -> float:
        """
        Calculate error rate for a group.
        
        Args:
            group_key: Error grouping key
            window_seconds: Time window in seconds
        
        Returns:
            Error rate (errors per second)
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Count recent errors
        recent_errors = sum(
            1 for ts in self.error_timestamps.get(group_key, [])
            if ts > cutoff
        )
        
        if window_seconds == 0:
            return 0.0
        
        return recent_errors / window_seconds
    
    # Circuit Breaker Methods
    
    def get_circuit_state(self, service_name: str) -> CircuitState:
        """Get the current circuit breaker state for a service."""
        return self.circuit_states[service_name]
    
    async def call_with_circuit_breaker(
        self,
        service_name: str,
        func,
        *args,
        **kwargs
    ):
        """
        Call a function with circuit breaker protection.
        
        Args:
            service_name: Name of the external service
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        state = self.circuit_states[service_name]
        
        # If circuit is open, check if timeout has passed
        if state == CircuitState.OPEN:
            last_failure = self.circuit_last_failure.get(service_name, 0)
            if time.time() - last_failure > self.circuit_timeout:
                # Move to half-open state
                self.circuit_states[service_name] = CircuitState.HALF_OPEN
                self.circuit_half_open_requests[service_name] = 0
                print(f"🔄 Circuit breaker for {service_name} entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker is OPEN for {service_name}")
        
        # If half-open, limit requests
        if state == CircuitState.HALF_OPEN:
            if self.circuit_half_open_requests[service_name] >= self.circuit_half_open_max_requests:
                raise Exception(f"Circuit breaker for {service_name} is HALF_OPEN (max test requests reached)")
            self.circuit_half_open_requests[service_name] += 1
        
        try:
            # Call the function
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if state == CircuitState.HALF_OPEN:
                self.circuit_states[service_name] = CircuitState.CLOSED
                self.circuit_failures[service_name] = 0
                print(f"✅ Circuit breaker for {service_name} returned to CLOSED state")
            else:
                self.circuit_failures[service_name] = max(0, self.circuit_failures[service_name] - 1)
            
            return result
        
        except Exception as error:
            # Failure - increment counter
            self.circuit_failures[service_name] += 1
            self.circuit_last_failure[service_name] = time.time()
            
            # Check if we should open the circuit
            if self.circuit_failures[service_name] >= self.circuit_failure_threshold:
                self.circuit_states[service_name] = CircuitState.OPEN
                print(f"⚠️  Circuit breaker for {service_name} is now OPEN")
            
            raise


# Global error service instance
_error_service: Optional[ErrorService] = None


def get_error_service() -> ErrorService:
    """Get the global error service instance."""
    global _error_service
    if _error_service is None:
        _error_service = ErrorService()
    return _error_service
