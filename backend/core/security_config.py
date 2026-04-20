"""
Security configuration for Glasswatch.

Centralized security settings for CORS, cookies, JWT, passwords, and API keys.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class CORSConfig(BaseModel):
    """CORS configuration."""
    
    allow_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
        ],
        description="Allowed origins for CORS"
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers"
    )
    max_age: int = Field(
        default=600,
        description="Max age for CORS preflight cache (seconds)"
    )
    
    @field_validator("allow_origins", mode="before")
    def validate_origins(cls, v):
        """Validate origin URLs."""
        if isinstance(v, str):
            v = [v]
        
        # In production, don't allow wildcards
        for origin in v:
            if origin == "*":
                raise ValueError("Wildcard origins (*) not allowed in production")
        
        return v


class CookieSecurityConfig(BaseModel):
    """Cookie security settings."""
    
    httponly: bool = Field(
        default=True,
        description="Prevent JavaScript access to cookies"
    )
    secure: bool = Field(
        default=True,
        description="Only send cookies over HTTPS"
    )
    samesite: str = Field(
        default="lax",
        description="SameSite cookie attribute (strict, lax, none)"
    )
    max_age: int = Field(
        default=3600,
        description="Cookie expiration in seconds"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Cookie domain"
    )
    path: str = Field(
        default="/",
        description="Cookie path"
    )
    
    @field_validator("samesite")
    def validate_samesite(cls, v):
        """Validate samesite value."""
        allowed = ["strict", "lax", "none"]
        if v.lower() not in allowed:
            raise ValueError(f"samesite must be one of {allowed}")
        return v.lower()


class JWTConfig(BaseModel):
    """JWT token configuration."""
    
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    token_url: str = Field(
        default="/api/v1/auth/token",
        description="Token endpoint URL"
    )
    issuer: str = Field(
        default="glasswatch",
        description="Token issuer"
    )
    audience: str = Field(
        default="glasswatch-api",
        description="Token audience"
    )
    
    @field_validator("algorithm")
    def validate_algorithm(cls, v):
        """Validate JWT algorithm."""
        allowed = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        if v not in allowed:
            raise ValueError(f"algorithm must be one of {allowed}")
        return v


class PasswordConfig(BaseModel):
    """Password and secret requirements."""
    
    min_length: int = Field(
        default=12,
        description="Minimum password length"
    )
    require_uppercase: bool = Field(
        default=True,
        description="Require uppercase letters"
    )
    require_lowercase: bool = Field(
        default=True,
        description="Require lowercase letters"
    )
    require_digits: bool = Field(
        default=True,
        description="Require digits"
    )
    require_special: bool = Field(
        default=True,
        description="Require special characters"
    )
    special_characters: str = Field(
        default="!@#$%^&*()_+-=[]{}|;:,.<>?",
        description="Allowed special characters"
    )
    max_age_days: Optional[int] = Field(
        default=90,
        description="Maximum password age in days (None for no expiration)"
    )
    
    def validate_password(self, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate a password against configured requirements.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters"
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.require_digits and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        if self.require_special and not any(c in self.special_characters for c in password):
            return False, f"Password must contain at least one special character: {self.special_characters}"
        
        return True, None


class APIKeyConfig(BaseModel):
    """API key format validation."""
    
    prefix: str = Field(
        default="gw_",
        description="API key prefix for identification"
    )
    length: int = Field(
        default=32,
        description="API key length (excluding prefix)"
    )
    allowed_chars: str = Field(
        default="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        description="Allowed characters in API key"
    )
    
    def validate_api_key(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Validate API key format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key.startswith(self.prefix):
            return False, f"API key must start with '{self.prefix}'"
        
        key_body = api_key[len(self.prefix):]
        
        if len(key_body) != self.length:
            return False, f"API key must be {self.length} characters (excluding prefix)"
        
        if not all(c in self.allowed_chars for c in key_body):
            return False, "API key contains invalid characters"
        
        return True, None
    
    def generate_pattern(self) -> str:
        """Generate regex pattern for API key validation."""
        return f"^{re.escape(self.prefix)}[{re.escape(self.allowed_chars)}]{{{self.length}}}$"


class SecurityConfig(BaseModel):
    """Main security configuration."""
    
    cors: CORSConfig = Field(default_factory=CORSConfig)
    cookie: CookieSecurityConfig = Field(default_factory=CookieSecurityConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    password: PasswordConfig = Field(default_factory=PasswordConfig)
    api_key: APIKeyConfig = Field(default_factory=APIKeyConfig)
    
    # Additional security settings
    enable_trusted_hosts: bool = Field(
        default=True,
        description="Enable trusted host validation"
    )
    trusted_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="List of trusted host names"
    )
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Requests per minute per IP"
    )


def get_security_config(env: str = "production") -> SecurityConfig:
    """
    Get security configuration for the specified environment.
    
    Args:
        env: Environment name (development, staging, production)
    
    Returns:
        SecurityConfig instance
    """
    if env == "development":
        return SecurityConfig(
            cors=CORSConfig(
                allow_origins=[
                    "http://localhost:3000",
                    "http://localhost:8000",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:8000",
                ],
            ),
            cookie=CookieSecurityConfig(
                secure=False,  # Allow HTTP in dev
                samesite="lax",
            ),
            jwt=JWTConfig(
                access_token_expire_minutes=60,  # Longer in dev
            ),
            password=PasswordConfig(
                min_length=8,  # Less strict in dev
                require_special=False,
            ),
            enable_rate_limiting=False,  # Disabled in dev
        )
    
    elif env == "staging":
        return SecurityConfig(
            cors=CORSConfig(
                allow_origins=[
                    "https://staging.glasswatch.io",
                    "https://staging-app.glasswatch.io",
                ],
            ),
            cookie=CookieSecurityConfig(
                secure=True,
                samesite="strict",
            ),
            jwt=JWTConfig(
                access_token_expire_minutes=30,
            ),
            password=PasswordConfig(
                min_length=12,
            ),
            trusted_hosts=[
                "staging.glasswatch.io",
                "staging-api.glasswatch.io",
            ],
            rate_limit_requests_per_minute=120,  # More lenient
        )
    
    else:  # production
        return SecurityConfig(
            cors=CORSConfig(
                allow_origins=[
                    "https://glasswatch.io",
                    "https://app.glasswatch.io",
                ],
            ),
            cookie=CookieSecurityConfig(
                secure=True,
                samesite="strict",
                max_age=1800,  # 30 minutes
            ),
            jwt=JWTConfig(
                access_token_expire_minutes=15,  # Shorter in production
                refresh_token_expire_days=7,
            ),
            password=PasswordConfig(
                min_length=14,  # Stricter in production
                max_age_days=90,
            ),
            trusted_hosts=[
                "glasswatch.io",
                "api.glasswatch.io",
                "app.glasswatch.io",
            ],
            rate_limit_requests_per_minute=60,
        )
