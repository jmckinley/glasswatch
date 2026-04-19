"""
Core utilities and configuration for Glasswatch backend.
"""
from backend.core.config import settings
from backend.core.auth import get_current_tenant

__all__ = ["settings", "get_current_tenant"]