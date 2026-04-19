"""
Configuration settings for Glasswatch
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # API Settings
    PROJECT_NAME: str = "Glasswatch"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:password@localhost/glasswatch"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Memgraph
    MEMGRAPH_URL: str = os.getenv("MEMGRAPH_URL", "bolt://localhost:7687")
    
    # External APIs
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    VULNCHECK_API_KEY: Optional[str] = os.getenv("VULNCHECK_API_KEY")
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = "us-east-1"
    
    # ServiceNow
    SERVICENOW_INSTANCE: Optional[str] = os.getenv("SERVICENOW_INSTANCE")
    SERVICENOW_USERNAME: Optional[str] = os.getenv("SERVICENOW_USERNAME")
    SERVICENOW_PASSWORD: Optional[str] = os.getenv("SERVICENOW_PASSWORD")
    
    # Jira
    JIRA_URL: Optional[str] = os.getenv("JIRA_URL")
    JIRA_EMAIL: Optional[str] = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN: Optional[str] = os.getenv("JIRA_API_TOKEN")
    
    # Features
    ENABLE_SNAPPER_INTEGRATION: bool = True
    ENABLE_PATCH_WEATHER: bool = True
    ENABLE_AI_PLANNER: bool = True
    
    # Tenant Settings
    MAX_ASSETS_PER_TENANT: int = 10000
    MAX_GOALS_PER_TENANT: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()