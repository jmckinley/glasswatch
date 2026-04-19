"""
API v1 router configuration.

Aggregates all v1 API endpoints.
"""
from fastapi import APIRouter

from backend.api.v1 import vulnerabilities, assets, goals

# Create main v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    vulnerabilities.router,
    prefix="/vulnerabilities",
    tags=["vulnerabilities"],
)

# Note: We'll uncomment these as we implement them
# api_router.include_router(
#     assets.router,
#     prefix="/assets",
#     tags=["assets"],
# )
# 
# api_router.include_router(
#     goals.router,
#     prefix="/goals",
#     tags=["goals"],
# )