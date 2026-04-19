#!/usr/bin/env python3
"""
Quick test to verify all imports work correctly.
"""
import sys
print("Testing Glasswatch imports...")

try:
    # Test core imports
    from backend.core.config import settings
    print("✓ Config loaded")
    print(f"  Project: {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"  Environment: {settings.ENV}")
    
    # Test database imports
    from backend.db.base import Base
    from backend.db.session import get_db, engine
    print("✓ Database modules loaded")
    
    # Test model imports
    from backend.models import (
        Tenant, Vulnerability, Asset, AssetVulnerability,
        Goal, Bundle, BundleItem, MaintenanceWindow
    )
    print("✓ All models imported successfully")
    
    # Test service imports
    from backend.services.scoring import scoring_service
    from backend.services.optimization import OptimizationService
    print("✓ Services loaded")
    
    # Test API imports
    from backend.api.v1 import api_router
    print("✓ API routes loaded")
    
    # Test auth
    from backend.core.auth import get_current_tenant
    print("✓ Auth module loaded")
    
    # Test main app
    from backend.main import app
    print("✓ FastAPI app created")
    
    print("\n✅ All imports successful! The backend structure is correct.")
    
    # Show some config
    print(f"\nConfiguration:")
    print(f"  Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"  Redis: {settings.REDIS_URL}")
    print(f"  CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)