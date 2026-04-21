"""
Glasswatch Backend API

The patch decision platform for the Mythos era.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1 import api_router
from backend.core.config import settings
from backend.core.security_config import get_security_config
from backend.middleware.security import SecurityHeadersMiddleware, get_security_headers_config
from backend.middleware.request_validation import RequestValidationMiddleware, get_request_validation_config
from backend.middleware.performance import PerformanceMiddleware, RequestSizeMiddleware
from backend.db.session import engine
from backend.db.base import Base
import backend.db.models  # noqa: F401 — register all models on Base.metadata
from backend.services.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks.
    """
    # Startup
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Initialize cache service
    await cache_service.connect()
    
    # Create database tables (for development - use Alembic in production)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    await cache_service.disconnect()
    await engine.dispose()
    print("👋 Shutting down Glasswatch")


# Load security configuration
security_config = get_security_config(env=settings.ENV)
security_headers_config = get_security_headers_config(env=settings.ENV)
request_validation_config = get_request_validation_config(env=settings.ENV)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Convert vulnerability chaos into organized, evidence-backed patch operations",
    lifespan=lifespan,
)

# Add security middlewares (order matters: outermost first)
# 1. Trusted Host Middleware (validate host header)
# Disabled when BACKEND_CORS_ORIGINS includes wildcards or Railway domains
# Railway handles host validation at the edge
if security_config.enable_trusted_hosts and settings.ENV not in ("production", "staging"):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=security_config.trusted_hosts,
    )

# 2. Security Headers Middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    **security_headers_config,
)

# 3. Request Validation Middleware
app.add_middleware(
    RequestValidationMiddleware,
    **request_validation_config,
)

# 4. Performance Middleware
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestSizeMiddleware, max_request_size=10 * 1024 * 1024)  # 10MB

# 5. CORS Middleware (must be last middleware before routes)
# Use BACKEND_CORS_ORIGINS from env if set (Railway), otherwise fall back to security_config
cors_origins = settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else security_config.cors.allow_origins
print(f"🌐 CORS origins: {cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=security_config.cors.allow_credentials,
    allow_methods=security_config.cors.allow_methods,
    allow_headers=security_config.cors.allow_headers,
    max_age=security_config.cors.max_age,
)


@app.get("/", response_class=JSONResponse)
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": "The patch decision platform for the Mythos era",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
    }


@app.get("/performance", response_class=JSONResponse)
async def performance_metrics():
    """
    Performance metrics endpoint.
    """
    from backend.db.pool import get_pool_stats, get_pool_recommendations
    from backend.db.optimization import QueryOptimizer
    
    pool_stats = await get_pool_stats(engine)
    recommendations = get_pool_recommendations(pool_stats)
    
    return {
        "database_pool": pool_stats,
        "recommendations": recommendations,
        "cache": cache_service.get_metrics(),
        "queries": QueryOptimizer.get_query_stats()
    }


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """
    Health check endpoint for Railway/load balancers.
    Always returns 200 if the process is alive.
    Use /health/detailed for dependency checks.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/health/detailed", response_class=JSONResponse)
async def health_detailed():
    """Detailed health check with dependency status."""
    from backend.db.pool import check_pool_health
    db_health = await check_pool_health(engine)
    cache_healthy = cache_service.is_available
    overall_healthy = db_health.get("healthy", False) and cache_healthy
    status_code = 200 if overall_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "degraded",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "checks": {
                "api": "ok",
                "database": "ok" if db_health.get("healthy") else "error",
                "redis": "ok" if cache_healthy else "unavailable",
            },
        }
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )