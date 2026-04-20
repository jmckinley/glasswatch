"""
API v1 router configuration.

Aggregates all v1 API endpoints.
"""
from fastapi import APIRouter

from backend.api.v1 import vulnerabilities, assets, goals, bundles, maintenance_windows, discovery

# Create main v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    vulnerabilities.router,
    prefix="/vulnerabilities",
    tags=["vulnerabilities"],
)

api_router.include_router(
    assets.router,
    prefix="/assets",
    tags=["assets"],
)

api_router.include_router(
    goals.router,
    prefix="/goals",
    tags=["goals"],
)

api_router.include_router(
    bundles.router,
    prefix="/bundles",
    tags=["bundles"],
)

api_router.include_router(
    maintenance_windows.router,
    prefix="/maintenance-windows",
    tags=["maintenance-windows"],
)

api_router.include_router(
    discovery.router,
    prefix="",  # Routes are already prefixed with /discovery
    tags=["discovery"],
)