"""
Request validation middleware for Glasswatch.

Implements request size limits, SQL injection detection, path traversal detection,
and rate limiting headers.
"""
import re
import structlog
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger()


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating and securing incoming requests.
    
    Features:
    - Request body size limits
    - SQL injection pattern detection
    - Path traversal detection
    - Rate limiting headers (for integration with rate limiter)
    """
    
    # SQL injection patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # SQL comment sequences
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # SQL operators
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # OR keyword
        r"((\%27)|(\'))union",  # UNION keyword
        r"exec(\s|\+)+(s|x)p\w+",  # Stored procedures
        r"UNION\s+SELECT",  # UNION SELECT
        r"INSERT\s+INTO",  # INSERT statements
        r"DELETE\s+FROM",  # DELETE statements
        r"DROP\s+TABLE",  # DROP TABLE
        r"UPDATE\s+\w+\s+SET",  # UPDATE statements
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # ../ sequences
        r"\.\.\%2F",  # URL encoded ../
        r"\.\.\%5C",  # URL encoded ..\
        r"%2e%2e/",  # Double URL encoded
        r"\.\.\\",  # Windows path traversal
    ]
    
    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB default
        enable_sql_injection_detection: bool = True,
        enable_path_traversal_detection: bool = True,
        rate_limit_per_minute: Optional[int] = None,
    ):
        super().__init__(app)
        self.max_body_size = max_body_size
        self.enable_sql_injection_detection = enable_sql_injection_detection
        self.enable_path_traversal_detection = enable_path_traversal_detection
        self.rate_limit_per_minute = rate_limit_per_minute
        
        # Compile regex patterns for performance
        self.sql_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS
        ]
        self.path_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PATH_TRAVERSAL_PATTERNS
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request and add security headers."""
        
        # Check request body size
        if "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_body_size:
                logger.warning(
                    "request_body_too_large",
                    size=content_length,
                    max_size=self.max_body_size,
                    path=request.url.path,
                )
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is {self.max_body_size} bytes."
                )
        
        # SQL injection detection on query parameters
        if self.enable_sql_injection_detection:
            query_string = str(request.url.query)
            if query_string:
                for pattern in self.sql_patterns:
                    if pattern.search(query_string):
                        logger.warning(
                            "sql_injection_attempt_detected",
                            pattern=pattern.pattern,
                            query=query_string,
                            path=request.url.path,
                            client=request.client.host if request.client else "unknown",
                        )
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid request parameters"
                        )
        
        # Path traversal detection
        if self.enable_path_traversal_detection:
            path = request.url.path
            for pattern in self.path_patterns:
                if pattern.search(path):
                    logger.warning(
                        "path_traversal_attempt_detected",
                        pattern=pattern.pattern,
                        path=path,
                        client=request.client.host if request.client else "unknown",
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid request path"
                    )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limiting headers (if rate limiter is configured)
        if self.rate_limit_per_minute:
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit_per_minute)
            # Note: Actual remaining count would come from Redis/rate limiter
            # This is a placeholder - implement with actual rate limiter
            response.headers["X-RateLimit-Remaining"] = str(self.rate_limit_per_minute)
        
        return response


def get_request_validation_config(env: str = "production"):
    """
    Get request validation configuration based on environment.
    
    Args:
        env: Environment name (development, staging, production)
    
    Returns:
        Configuration dict for RequestValidationMiddleware
    """
    if env == "development":
        return {
            "max_body_size": 50 * 1024 * 1024,  # 50MB for dev (testing)
            "enable_sql_injection_detection": True,
            "enable_path_traversal_detection": True,
            "rate_limit_per_minute": None,  # Disabled in dev
        }
    elif env == "staging":
        return {
            "max_body_size": 20 * 1024 * 1024,  # 20MB for staging
            "enable_sql_injection_detection": True,
            "enable_path_traversal_detection": True,
            "rate_limit_per_minute": 120,  # More lenient in staging
        }
    else:  # production
        return {
            "max_body_size": 10 * 1024 * 1024,  # 10MB for production
            "enable_sql_injection_detection": True,
            "enable_path_traversal_detection": True,
            "rate_limit_per_minute": 60,  # 60 requests per minute
        }
