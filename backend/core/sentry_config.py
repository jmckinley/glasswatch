"""
Sentry integration for error tracking and performance monitoring.

Configures Sentry SDK with environment-specific settings, PII filtering,
and performance tracing.
"""
import os
import re
from typing import Any, Dict, Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration


# Sensitive data patterns to scrub
SENSITIVE_PATTERNS = [
    # Authentication
    r'password',
    r'passwd',
    r'secret',
    r'token',
    r'api[_-]?key',
    r'access[_-]?key',
    r'private[_-]?key',
    r'auth',
    r'authorization',
    r'bearer',
    r'cookie',
    r'session',
    
    # Personal info
    r'ssn',
    r'social[_-]?security',
    r'credit[_-]?card',
    r'card[_-]?number',
    r'cvv',
    r'tax[_-]?id',
    
    # AWS
    r'aws[_-]?secret',
    r'aws[_-]?access',
]

# Compile patterns for efficiency
SENSITIVE_REGEX = re.compile('|'.join(SENSITIVE_PATTERNS), re.IGNORECASE)


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter sensitive data before sending to Sentry.
    
    Args:
        event: Sentry event data
        hint: Additional context
    
    Returns:
        Filtered event or None to drop the event
    """
    # Scrub request data
    if 'request' in event:
        request = event['request']
        
        # Scrub headers
        if 'headers' in request:
            request['headers'] = scrub_dict(request['headers'])
        
        # Scrub cookies
        if 'cookies' in request:
            request['cookies'] = scrub_dict(request['cookies'])
        
        # Scrub query string
        if 'query_string' in request:
            request['query_string'] = scrub_dict(request['query_string'])
        
        # Scrub POST data
        if 'data' in request:
            if isinstance(request['data'], dict):
                request['data'] = scrub_dict(request['data'])
    
    # Scrub extra data
    if 'extra' in event:
        event['extra'] = scrub_dict(event['extra'])
    
    # Scrub user data (keep ID but remove sensitive fields)
    if 'user' in event:
        user = event['user']
        allowed_fields = {'id', 'username', 'ip_address'}
        event['user'] = {k: v for k, v in user.items() if k in allowed_fields}
    
    # Scrub breadcrumbs
    if 'breadcrumbs' in event:
        for crumb in event['breadcrumbs'].get('values', []):
            if 'data' in crumb:
                crumb['data'] = scrub_dict(crumb['data'])
    
    return event


def scrub_dict(data: Dict[str, Any], placeholder: str = "[REDACTED]") -> Dict[str, Any]:
    """
    Recursively scrub sensitive data from a dictionary.
    
    Args:
        data: Dictionary to scrub
        placeholder: Replacement value for sensitive data
    
    Returns:
        Scrubbed dictionary
    """
    if not isinstance(data, dict):
        return data
    
    scrubbed = {}
    for key, value in data.items():
        # Check if key matches sensitive pattern
        if SENSITIVE_REGEX.search(str(key)):
            scrubbed[key] = placeholder
        # Recursively scrub nested dicts
        elif isinstance(value, dict):
            scrubbed[key] = scrub_dict(value, placeholder)
        # Scrub lists of dicts
        elif isinstance(value, list):
            scrubbed[key] = [
                scrub_dict(item, placeholder) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            scrubbed[key] = value
    
    return scrubbed


def before_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter breadcrumbs before adding to Sentry.
    
    Args:
        crumb: Breadcrumb data
        hint: Additional context
    
    Returns:
        Filtered breadcrumb or None to drop it
    """
    # Skip noisy breadcrumbs
    if crumb.get('category') in ['httplib', 'urllib3']:
        return None
    
    # Scrub data in breadcrumb
    if 'data' in crumb:
        crumb['data'] = scrub_dict(crumb['data'])
    
    return crumb


def get_git_release() -> Optional[str]:
    """
    Get the current git SHA for release tracking.
    
    Returns:
        Git SHA or None if not in a git repository
    """
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    return None


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    debug: bool = False,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
) -> bool:
    """
    Initialize Sentry SDK with comprehensive configuration.
    
    Args:
        dsn: Sentry DSN (defaults to SENTRY_DSN env var)
        environment: Environment name (development, staging, production)
        debug: Enable debug mode
        traces_sample_rate: Percentage of transactions to trace (0.0-1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0-1.0)
    
    Returns:
        True if Sentry was initialized, False otherwise
    """
    # Get DSN from parameter or environment
    dsn = dsn or os.getenv("SENTRY_DSN")
    
    if not dsn:
        print("⚠️  Sentry DSN not configured - error tracking disabled")
        return False
    
    # Adjust sample rates by environment
    if environment == "production":
        traces_sample_rate = traces_sample_rate or 0.2
        profiles_sample_rate = profiles_sample_rate or 0.1
    elif environment == "staging":
        traces_sample_rate = traces_sample_rate or 0.5
        profiles_sample_rate = profiles_sample_rate or 0.2
    else:  # development
        traces_sample_rate = traces_sample_rate or 1.0
        profiles_sample_rate = profiles_sample_rate or 0.0  # Disable profiling in dev
    
    # Get release version
    release = get_git_release()
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        debug=debug,
        
        # Performance monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        
        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # Group by endpoint, not URL
            ),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        
        # Data filtering
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
        
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send PII by default
        max_breadcrumbs=50,
        
        # Ignore common errors
        ignore_errors=[
            KeyboardInterrupt,
            "BrokenPipeError",
            "ConnectionResetError",
        ],
    )
    
    print(f"✅ Sentry initialized for environment: {environment}")
    if release:
        print(f"   Release: {release}")
    print(f"   Traces sample rate: {traces_sample_rate * 100}%")
    
    return True


def set_user_context(
    user_id: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Set user context for Sentry events.
    
    Args:
        user_id: User identifier
        username: Optional username
        email: Optional email (will be scrubbed if send_default_pii=False)
        tenant_id: Optional tenant identifier
    """
    context = {
        "id": user_id,
    }
    
    if username:
        context["username"] = username
    
    if email:
        context["email"] = email
    
    if tenant_id:
        context["tenant_id"] = tenant_id
    
    sentry_sdk.set_user(context)


def set_context(key: str, data: Dict[str, Any]):
    """
    Set custom context for Sentry events.
    
    Args:
        key: Context key
        data: Context data (will be scrubbed)
    """
    scrubbed_data = scrub_dict(data)
    sentry_sdk.set_context(key, scrubbed_data)


def capture_message(message: str, level: str = "info", **kwargs):
    """
    Capture a message in Sentry.
    
    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context
    """
    sentry_sdk.capture_message(message, level=level, **kwargs)


def capture_exception(error: Exception, **kwargs):
    """
    Capture an exception in Sentry.
    
    Args:
        error: Exception to capture
        **kwargs: Additional context
    """
    sentry_sdk.capture_exception(error, **kwargs)
