"""
Comment model - Team collaboration and discussion
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Enum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from backend.db.base import Base


class EntityType(str, enum.Enum):
    """Types of entities that can be commented on"""
    ASSET = "asset"
    VULNERABILITY = "vulnerability"
    BUNDLE = "bundle"
    GOAL = "goal"
    APPROVAL = "approval"


class Comment(Base):
    """
    Comment model for team collaboration
    
    Supports:
    - Threaded replies via parent_id
    - @mentions for user notifications
    - Soft delete to preserve conversation history
    - Polymorphic entity references
    """
    __tablename__ = "comments"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Tenant relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Entity reference (polymorphic)
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Author
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Threading support
    parent_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    
    # Content
    content = Column(Text, nullable=False)
    mentions = Column(JSON, default=list, nullable=False)  # List of user UUIDs that were @mentioned
    
    # Edit tracking
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    parent = relationship("Comment", remote_side=[id], backref="replies")
    reactions = relationship("Reaction", back_populates="comment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Comment {self.id} by {self.user_id} on {self.entity_type}:{self.entity_id}>"
    
    def to_dict(self):
        """Convert comment to dict for API responses"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "entity_type": self.entity_type.value,
            "entity_id": str(self.entity_id),
            "user_id": str(self.user_id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "content": self.content if not self.is_deleted else "[deleted]",
            "mentions": [str(uid) for uid in self.mentions],
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Reaction(Base):
    """
    Reaction model for comment reactions (emoji)
    
    Users can react to comments with emoji.
    Each user can only have one instance of each emoji per comment.
    """
    __tablename__ = "reactions"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Foreign keys
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Reaction
    emoji = Column(String(20), nullable=False)  # e.g., "thumbsup", "eyes", "rocket"
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    comment = relationship("Comment", back_populates="reactions")
    user = relationship("User")
    
    # Unique constraint: one user can only have one instance of each emoji per comment
    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', 'emoji', name='uq_reaction_user_emoji'),
    )
    
    def __repr__(self):
        return f"<Reaction {self.emoji} by {self.user_id} on {self.comment_id}>"
    
    def to_dict(self):
        """Convert reaction to dict for API responses"""
        return {
            "id": str(self.id),
            "comment_id": str(self.comment_id),
            "user_id": str(self.user_id),
            "emoji": self.emoji,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
