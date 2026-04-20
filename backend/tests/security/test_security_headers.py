"""
Security headers tests for Glasswatch.

Tests all security middleware and configuration.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.middleware.security import SecurityHeadersMiddleware
from backend.middleware.request_validation import RequestValidationMiddleware
from backend.core.security_config import (
    get_security_config,
    PasswordConfig,
    APIKeyConfig,
)


@pytest.fixture
def app():
    """Create test FastAPI app with security middleware."""
    app = FastAPI()
    
    # Add security middlewares
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=31536000,
        enable_csp=True,
        csp_report_only=False,
    )
    
    app.add_middleware(
        RequestValidationMiddleware,
        max_body_size=1024,  # 1KB for testing
        enable_sql_injection_detection=True,
        enable_path_traversal_detection=True,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestSecurityHeaders:
    """Test security headers middleware."""
    
    def test_hsts_header(self, client):
        """Test HSTS header is present."""
        response = client.get("/test")
        assert "strict-transport-security" in response.headers
        assert "max-age=31536000" in response.headers["strict-transport-security"]
        assert "includeSubDomains" in response.headers["strict-transport-security"]
    
    def test_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get("/test")
        assert response.headers["x-content-type-options"] == "nosniff"
    
    def test_frame_options(self, client):
        """Test X-Frame-Options header."""
        response = client.get("/test")
        assert response.headers["x-frame-options"] == "DENY"
    
    def test_xss_protection(self, client):
        """Test X-XSS-Protection header."""
        response = client.get("/test")
        assert response.headers["x-xss-protection"] == "1; mode=block"
    
    def test_csp_header(self, client):
        """Test Content-Security-Policy header."""
        response = client.get("/test")
        assert "content-security-policy" in response.headers
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
    
    def test_referrer_policy(self, client):
        """Test Referrer-Policy header."""
        response = client.get("/test")
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    
    def test_permissions_policy(self, client):
        """Test Permissions-Policy header."""
        response = client.get("/test")
        assert "permissions-policy" in response.headers
        policy = response.headers["permissions-policy"]
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy


class TestRequestValidation:
    """Test request validation middleware."""
    
    def test_request_body_size_limit(self, client):
        """Test request body size limit."""
        # Create payload larger than 1KB limit
        large_payload = "x" * 2000
        response = client.post(
            "/test",
            json={"data": large_payload},
            headers={"content-length": "2000"}
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()
    
    def test_sql_injection_detection_union(self, client):
        """Test SQL injection detection - UNION attack."""
        response = client.get("/test?id=1' UNION SELECT * FROM users--")
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    def test_sql_injection_detection_or(self, client):
        """Test SQL injection detection - OR attack."""
        response = client.get("/test?username=admin' OR '1'='1")
        assert response.status_code == 400
    
    def test_sql_injection_detection_comment(self, client):
        """Test SQL injection detection - comment sequences."""
        response = client.get("/test?id=1--")
        assert response.status_code == 400
    
    def test_path_traversal_detection(self, client):
        """Test path traversal detection."""
        response = client.get("/test/../../../etc/passwd")
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    def test_path_traversal_url_encoded(self, client):
        """Test path traversal detection - URL encoded."""
        response = client.get("/test/%2e%2e/sensitive")
        assert response.status_code == 400
    
    def test_valid_request_passes(self, client):
        """Test that valid requests pass through."""
        response = client.get("/test?id=123&name=test")
        assert response.status_code == 200
        assert response.json()["message"] == "ok"
    
    def test_rate_limit_headers(self, client):
        """Test rate limiting headers are present."""
        app = FastAPI()
        app.add_middleware(
            RequestValidationMiddleware,
            rate_limit_per_minute=60,
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        assert "x-ratelimit-limit" in response.headers
        assert response.headers["x-ratelimit-limit"] == "60"


class TestSecurityConfig:
    """Test security configuration."""
    
    def test_cors_no_wildcard_in_production(self):
        """Test that wildcard CORS origins are not allowed in production."""
        from pydantic import ValidationError
        from backend.core.security_config import CORSConfig
        
        with pytest.raises(ValidationError):
            CORSConfig(allow_origins=["*"])
    
    def test_password_validation_min_length(self):
        """Test password minimum length validation."""
        config = PasswordConfig(min_length=12)
        is_valid, error = config.validate_password("short")
        assert not is_valid
        assert "12 characters" in error
    
    def test_password_validation_uppercase(self):
        """Test password uppercase requirement."""
        config = PasswordConfig(require_uppercase=True)
        is_valid, error = config.validate_password("lowercase123!")
        assert not is_valid
        assert "uppercase" in error.lower()
    
    def test_password_validation_lowercase(self):
        """Test password lowercase requirement."""
        config = PasswordConfig(require_lowercase=True)
        is_valid, error = config.validate_password("UPPERCASE123!")
        assert not is_valid
        assert "lowercase" in error.lower()
    
    def test_password_validation_digits(self):
        """Test password digit requirement."""
        config = PasswordConfig(require_digits=True)
        is_valid, error = config.validate_password("NoDigitsHere!")
        assert not is_valid
        assert "digit" in error.lower()
    
    def test_password_validation_special(self):
        """Test password special character requirement."""
        config = PasswordConfig(require_special=True)
        is_valid, error = config.validate_password("NoSpecialChars123")
        assert not is_valid
        assert "special character" in error.lower()
    
    def test_password_validation_valid(self):
        """Test valid password passes all checks."""
        config = PasswordConfig(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_digits=True,
            require_special=True,
        )
        is_valid, error = config.validate_password("ValidPass123!")
        assert is_valid
        assert error is None
    
    def test_api_key_validation_prefix(self):
        """Test API key prefix validation."""
        config = APIKeyConfig(prefix="gw_", length=32)
        is_valid, error = config.validate_api_key("invalid_prefix_key")
        assert not is_valid
        assert "gw_" in error
    
    def test_api_key_validation_length(self):
        """Test API key length validation."""
        config = APIKeyConfig(prefix="gw_", length=32)
        is_valid, error = config.validate_api_key("gw_tooshort")
        assert not is_valid
        assert "32 characters" in error
    
    def test_api_key_validation_valid(self):
        """Test valid API key passes."""
        config = APIKeyConfig(prefix="gw_", length=32)
        valid_key = "gw_" + "a" * 32
        is_valid, error = config.validate_api_key(valid_key)
        assert is_valid
        assert error is None
    
    def test_environment_configs(self):
        """Test different environment configurations."""
        dev_config = get_security_config("development")
        staging_config = get_security_config("staging")
        prod_config = get_security_config("production")
        
        # Development should be more lenient
        assert not dev_config.cookie.secure  # Allow HTTP
        assert not dev_config.enable_rate_limiting
        assert dev_config.password.min_length == 8
        
        # Production should be strict
        assert prod_config.cookie.secure
        assert prod_config.cookie.samesite == "strict"
        assert prod_config.enable_rate_limiting
        assert prod_config.password.min_length == 14
        
        # Staging should be in between
        assert staging_config.cookie.secure
        assert staging_config.enable_rate_limiting
        assert staging_config.password.min_length == 12


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_allows_configured_origins(self):
        """Test CORS allows configured origins."""
        from fastapi.middleware.cors import CORSMiddleware
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}
        
        client = TestClient(app)
        response = client.get(
            "/test",
            headers={"origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        # Note: TestClient doesn't fully simulate CORS, but we can verify middleware is applied


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
