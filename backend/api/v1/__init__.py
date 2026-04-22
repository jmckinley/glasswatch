"""
API v1 router configuration.

Aggregates all v1 API endpoints.
"""
from fastapi import APIRouter

from backend.api.v1 import vulnerabilities, assets, goals, bundles, maintenance_windows, discovery, auth, audit, users, approvals, comments, activities, snapshots, simulator, dashboard, slack, connections, onboarding, settings, tags, rules, notifications

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

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
)

api_router.include_router(
    audit.router,
    prefix="",
    tags=["audit"],
)

api_router.include_router(
    users.router,
    prefix="",
    tags=["users"],
)

api_router.include_router(
    approvals.router,
    prefix="",
    tags=["approvals"],
)

api_router.include_router(
    comments.router,
    prefix="/comments",
    tags=["comments"],
)

api_router.include_router(
    activities.router,
    prefix="/activities",
    tags=["activities"],
)

api_router.include_router(
    snapshots.router,
    prefix="/snapshots",
    tags=["snapshots"],
)

api_router.include_router(
    simulator.router,
    prefix="/simulator",
    tags=["simulator"],
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)

api_router.include_router(
    slack.router,
    prefix="/slack",
    tags=["slack"],
)

api_router.include_router(
    connections.router,
    prefix="/connections",
    tags=["connections"],
)

api_router.include_router(
    onboarding.router,
    prefix="/onboarding",
    tags=["onboarding"],
)

api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["settings"],
)

api_router.include_router(
    tags.router,
    prefix="/tags",
    tags=["tags"],
)

api_router.include_router(
    rules.router,
    prefix="/rules",
    tags=["rules"],
)

api_router.include_router(
    notifications.router,
    prefix="",
    tags=["notifications"],
)