"""
Database session management
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from backend.core.config import settings
from backend.db.pool import create_optimized_engine

# Create async engine with optimized connection pool
engine = create_optimized_engine(
    database_url=settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create declarative base
Base = declarative_base()


# Dependency to get DB session
async def get_db() -> AsyncSession:
    """
    Dependency to get database session
    
    Usage:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()