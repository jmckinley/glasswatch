"""
Glasswatch Backend API

The patch decision platform for the Mythos era.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1 import api_router
from backend.core.config import settings
from backend.db.session import engine
from backend.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks.
    """
    # Startup
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Create database tables (for development - use Alembic in production)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    await engine.dispose()
    print("👋 Shutting down Glasswatch")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Convert vulnerability chaos into organized, evidence-backed patch operations",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    # TODO: Add database connectivity check
    # TODO: Add Redis connectivity check
    # TODO: Add external service checks
    
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": {
            "api": "ok",
            "database": "ok",  # TODO: Implement actual check
            "redis": "ok",     # TODO: Implement actual check
        }
    }


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