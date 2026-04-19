"""
API v1 router configuration.

Aggregates all v1 API endpoints.
"""
from fastapi import APIRouter

from backend.api.v1 import vulnerabilities, assets, goals, bundles, maintenance_windows

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

router.include_router(
    goals.router,
    prefix="/goals",
    tags=["goals"],
)

router.include_router(
    bundles.router,
    prefix="/bundles",
    tags=["bundles"],
)

router.include_router(
    maintenance_windows.router,
    prefix="/maintenance-windows",
    tags=["maintenance-windows"],
)

# Note: We'll uncomment these as we implement them
# api_router.include_router(
#     goals.router,
#     prefix="/goals",
#     tags=["goals"],
# )