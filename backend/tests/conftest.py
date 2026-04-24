"""
Test fixtures and configuration for Glasswatch backend tests.

Provides:
- Async test database setup
- FastAPI test client
- Factory fixtures for creating test data
- Auth fixtures for authenticated requests
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from uuid import uuid4
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Patch SQLite compiler to handle PostgreSQL-specific types
# (JSONB, ARRAY, UUID) by substituting SQLite-compatible equivalents.
# This is required because the models were written for PostgreSQL but
# tests use in-memory SQLite for speed.
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTypeCompiler

def _visit_JSONB(self, type_, **kw):
    return "TEXT"

def _visit_ARRAY(self, type_, **kw):
    return "TEXT"

def _visit_UUID(self, type_, **kw):
    return "TEXT"

_SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
_SQLiteTypeCompiler.visit_ARRAY = _visit_ARRAY
_SQLiteTypeCompiler.visit_UUID = _visit_UUID

from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app
from backend.models.tenant import Tenant
from backend.models.user import User, UserRole
from backend.models.vulnerability import Vulnerability
from backend.models.asset import Asset
from backend.models.bundle import Bundle
from backend.models.asset_vulnerability import AssetVulnerability
from backend.core.auth_workos import create_access_token


# Test database URL
# Use PostgreSQL test database if available, else fall back to SQLite.
# Note: SQLite doesn't support JSONB, so some models need to use JSON for tests.
import os as _os
TEST_DATABASE_URL = _os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with dependency overrides."""
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# Factory fixtures for creating test data

@pytest_asyncio.fixture
async def create_test_tenant(test_session: AsyncSession):
    """Factory fixture to create test tenants."""
    async def _create_tenant(
        name: str = "Test Tenant",
        email: str = "test@example.com",
        region: str = "us-east-1",
        tier: str = "trial",
        is_active: bool = True,
    ) -> Tenant:
        tenant = Tenant(
            id=uuid4(),
            name=name,
            email=email,
            region=region,
            tier=tier,
            is_active=is_active,
            encryption_key_id=f"key_{uuid4()}",
            settings={}
        )
        test_session.add(tenant)
        await test_session.flush()
        await test_session.refresh(tenant)
        return tenant
    
    return _create_tenant


@pytest_asyncio.fixture
async def create_test_user(test_session: AsyncSession):
    """Factory fixture to create test users."""
    async def _create_user(
        tenant_id,
        email: str = "user@example.com",
        name: str = "Test User",
        role: UserRole = UserRole.ENGINEER,
        is_active: bool = True,
    ) -> User:
        from uuid import UUID as _UUID
        if isinstance(tenant_id, str):
            tenant_id = _UUID(tenant_id)
        user = User(
            id=uuid4(),
            tenant_id=tenant_id,
            email=email,
            name=name,
            role=role,
            is_active=is_active,
            workos_user_id=f"workos_{uuid4()}",
            preferences={}
        )
        test_session.add(user)
        await test_session.flush()
        await test_session.refresh(user)
        return user
    
    return _create_user


@pytest_asyncio.fixture
async def create_test_vulnerability(test_session: AsyncSession):
    """Factory fixture to create test vulnerabilities."""
    async def _create_vulnerability(
        identifier: str = "CVE-2024-0001",
        severity: str = "HIGH",
        epss_score: float = 0.5,
        kev_listed: bool = False,
        # Legacy aliases kept for backwards compat
        tenant_id: str = None,
        cve_id: str = None,
        in_kev: bool = False,
    ) -> Vulnerability:
        # Support legacy cve_id / in_kev param names
        if cve_id:
            identifier = cve_id
        if in_kev:
            kev_listed = True
        vuln = Vulnerability(
            id=uuid4(),
            identifier=identifier,
            source="nvd",
            title=f"Test Vulnerability {identifier}",
            description="Test vulnerability description",
            severity=severity,
            cvss_score=7.5,
            epss_score=epss_score,
            kev_listed=kev_listed,
            patch_available=True,
            published_at=datetime.now(timezone.utc),
            affected_products=["test-product"],
        )
        test_session.add(vuln)
        await test_session.flush()
        await test_session.refresh(vuln)
        return vuln

    return _create_vulnerability


@pytest_asyncio.fixture
async def create_test_asset(test_session: AsyncSession):
    """Factory fixture to create test assets."""
    async def _create_asset(
        tenant_id: str,
        hostname: str = "test-server",  # maps to identifier
        ip_address: str = "10.0.0.1",
        criticality: int = 3,
        is_internet_facing: bool = False,
        runtime_loaded: bool = False,
        runtime_executed: bool = False,
    ) -> Asset:
        from uuid import UUID as _UUID
        # Normalize tenant_id to UUID object for SQLAlchemy
        if isinstance(tenant_id, str):
            tenant_id = _UUID(tenant_id)
        # Map legacy is_internet_facing to exposure field
        exposure = "INTERNET" if is_internet_facing else "ISOLATED"
        asset = Asset(
            id=uuid4(),
            tenant_id=tenant_id,
            identifier=hostname,
            name=hostname,
            type="server",
            criticality=criticality,
            exposure=exposure,
            os_family="linux",
            os_version="22.04",
            environment="production",
            ip_addresses=[ip_address],
            running_services=["nginx", "postgresql"],
            tags=["env:test"],
        )
        test_session.add(asset)
        await test_session.flush()
        await test_session.refresh(asset)
        return asset

    return _create_asset


@pytest_asyncio.fixture
async def create_test_bundle(test_session: AsyncSession):
    """Factory fixture to create test bundles."""
    async def _create_bundle(
        tenant_id,
        name: str = "Test Bundle",
        description: str = "Test bundle description",
        status: str = "draft",
        priority: int = 3,
        # Extra kwargs passed through to Bundle model
        **kwargs,
    ) -> Bundle:
        from uuid import UUID as _UUID
        if isinstance(tenant_id, str):
            tenant_id = _UUID(tenant_id)
        # Map legacy kwarg names to actual model fields
        if 'affected_asset_count' in kwargs:
            kwargs['assets_affected_count'] = kwargs.pop('affected_asset_count')
        if 'estimated_downtime' in kwargs:
            kwargs['estimated_duration_minutes'] = kwargs.pop('estimated_downtime')
        bundle = Bundle(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            status=status,
            risk_score=kwargs.pop('risk_score', priority * 10.0),
            assets_affected_count=kwargs.pop('assets_affected_count', 0),
            **kwargs,
        )
        test_session.add(bundle)
        await test_session.flush()
        await test_session.refresh(bundle)
        return bundle
    
    return _create_bundle


# Auth fixtures

@pytest_asyncio.fixture
async def test_tenant(create_test_tenant) -> Tenant:
    """Create a default test tenant."""
    return await create_test_tenant()


@pytest_asyncio.fixture
async def test_user(create_test_user, test_tenant: Tenant) -> User:
    """Create a default test user (engineer role)."""
    return await create_test_user(
        tenant_id=str(test_tenant.id),
        email="engineer@example.com",
        name="Test Engineer",
        role=UserRole.ENGINEER
    )


@pytest_asyncio.fixture
async def admin_user(create_test_user, test_tenant: Tenant) -> User:
    """Create an admin user."""
    return await create_test_user(
        tenant_id=str(test_tenant.id),
        email="admin@example.com",
        name="Test Admin",
        role=UserRole.ADMIN
    )


@pytest_asyncio.fixture
async def viewer_user(create_test_user, test_tenant: Tenant) -> User:
    """Create a viewer user."""
    return await create_test_user(
        tenant_id=str(test_tenant.id),
        email="viewer@example.com",
        name="Test Viewer",
        role=UserRole.VIEWER
    )


@pytest_asyncio.fixture
async def authenticated_client(test_session: AsyncSession, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated client (engineer role) with its own AsyncClient instance.

    This fixture creates a *separate* AsyncClient so that tests requiring both
    ``authenticated_client`` and ``admin_client`` don't share the same underlying
    client object (and inadvertently overwrite each other's Authorization header).
    """
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    token = await create_access_token(user_id=str(test_user.id), tenant_id=str(test_user.tenant_id))
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest_asyncio.fixture
async def admin_client(test_session: AsyncSession, admin_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated admin client with its own AsyncClient instance.

    Independent from the shared ``client`` fixture — see ``authenticated_client``
    for the rationale.
    """
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    token = await create_access_token(user_id=str(admin_user.id), tenant_id=str(admin_user.tenant_id))
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest_asyncio.fixture
async def viewer_client(test_session: AsyncSession, viewer_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated viewer client with its own AsyncClient instance.

    Independent from the shared ``client`` fixture — see ``authenticated_client``
    for the rationale.
    """
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    token = await create_access_token(user_id=str(viewer_user.id), tenant_id=str(viewer_user.tenant_id))
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
