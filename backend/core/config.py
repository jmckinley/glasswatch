"""
Application configuration using Pydantic settings.

Loads from environment variables and .env file.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # Basic app info
    PROJECT_NAME: str = "PatchGuide"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://glasswatch:glasswatch-secret@localhost:5432/glasswatch"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://frontend:3000",  # Docker service name
    ]
    
    # External APIs (optional)
    NVD_API_KEY: Optional[str] = None
    EPSS_API_URL: str = "https://api.first.org/data/v1/epss"
    
    # WorkOS (for production auth)
    WORKOS_API_KEY: Optional[str] = None
    WORKOS_CLIENT_ID: Optional[str] = None
    
    # AWS (for KMS encryption)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Snapper Runtime Integration
    SNAPPER_API_URL: Optional[str] = None
    SNAPPER_API_KEY: Optional[str] = None
    
    # Patch Weather Service
    PATCH_WEATHER_ENABLED: bool = True
    PATCH_WEATHER_MIN_REPORTS: int = 5
    
    # Optimization settings
    OPTIMIZATION_MAX_TIME_SECONDS: int = 30
    OPTIMIZATION_DEFAULT_WINDOWS: int = 12
    
    @field_validator("DATABASE_URL", mode="before")
    def normalize_database_url(cls, v: str) -> str:
        """Railway provides postgresql:// — convert to postgresql+asyncpg:// for SQLAlchemy async."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v


# Create settings instance
settings = Settings()

# Log configuration on startup (hide sensitive values)
if settings.DEBUG:
    print(f"🔧 Configuration loaded for environment: {settings.ENV}")
    print(f"   - Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"   - Redis: {settings.REDIS_URL}")
    print(f"   - CORS Origins: {settings.BACKEND_CORS_ORIGINS}")