"""
User model - Individual users within tenants
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from backend.db.base import Base


class UserRole(str, enum.Enum):
    """User roles within a tenant"""
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    APPROVER = "approver"


class User(Base):
    """
    User model for authentication and authorization
    
    Each user:
    - Belongs to a tenant
    - Has a role for RBAC
    - Can authenticate via WorkOS SSO
    - Has audit trail of actions
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Tenant relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Basic info
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    
    # Authentication
    workos_user_id = Column(String(255), nullable=True, unique=True)  # WorkOS user ID
    oauth_provider = Column(String(50), nullable=True)  # google, github, etc.
    oauth_id = Column(String(255), nullable=True)  # Provider-specific user ID
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Authorization
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    permissions = Column(JSON, default=dict, nullable=False)  # Additional granular permissions
    
    # API access
    api_key_hash = Column(String(255), nullable=True)  # For programmatic access
    api_key_last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    preferences = Column(JSON, default=dict, nullable=False)  # UI preferences, notification settings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", backref="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    approval_actions = relationship("ApprovalAction", back_populates="user")
    
    # Unique constraint on email per tenant
    __table_args__ = (
        {},
    )
    
    def __repr__(self):
        return f"<User {self.email} ({self.role}) in {self.tenant_id}>"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        # Admins have all permissions
        if self.role == UserRole.ADMIN:
            return True
            
        # Check role-based defaults
        role_permissions = {
            UserRole.ENGINEER: [
                "bundles:read", "bundles:write", 
                "assets:read", "assets:write",
                "goals:read", "schedule:read"
            ],
            UserRole.APPROVER: [
                "bundles:read", "bundles:approve",
                "assets:read", "schedule:read",
                "approvals:write"
            ],
            UserRole.VIEWER: [
                "bundles:read", "assets:read",
                "goals:read", "schedule:read",
                "reports:read"
            ]
        }
        
        if permission in role_permissions.get(self.role, []):
            return True
            
        # Check additional permissions
        return permission in self.permissions.get("additional", [])