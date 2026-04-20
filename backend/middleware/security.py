"""
Security headers middleware for Glasswatch.

Implements comprehensive security headers following OWASP best practices.
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Headers implemented:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        csp_report_only: bool = False,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.csp_report_only = csp_report_only
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        
        # HSTS - Force HTTPS for 1 year, include subdomains
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.hsts_max_age}; includeSubDomains; preload"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        if self.enable_csp:
            # Strict CSP but allow API docs (Swagger UI needs inline scripts)
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Allow Swagger UI
                "style-src 'self' 'unsafe-inline'",  # Allow Swagger UI
                "img-src 'self' data: https:",  # Allow data URIs and external images for docs
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",  # Same as X-Frame-Options DENY
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
                "upgrade-insecure-requests",
            ]
            
            csp_header = "Content-Security-Policy-Report-Only" if self.csp_report_only else "Content-Security-Policy"
            response.headers[csp_header] = "; ".join(csp_directives)
        
        # Referrer Policy - Only send referrer for same-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - Disable unnecessary browser features
        permissions_directives = [
            "camera=()",  # Disable camera
            "microphone=()",  # Disable microphone
            "geolocation=()",  # Disable geolocation
            "interest-cohort=()",  # Disable FLoC tracking
            "payment=()",  # Disable payment APIs
            "usb=()",  # Disable USB access
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)
        
        return response


def get_security_headers_config(env: str = "production"):
    """
    Get security headers configuration based on environment.
    
    Args:
        env: Environment name (development, staging, production)
    
    Returns:
        Configuration dict for SecurityHeadersMiddleware
    """
    if env == "development":
        return {
            "hsts_max_age": 3600,  # 1 hour for dev
            "enable_csp": True,
            "csp_report_only": True,  # Report-only mode in dev
        }
    elif env == "staging":
        return {
            "hsts_max_age": 86400,  # 1 day for staging
            "enable_csp": True,
            "csp_report_only": False,
        }
    else:  # production
        return {
            "hsts_max_age": 31536000,  # 1 year
            "enable_csp": True,
            "csp_report_only": False,
        }
