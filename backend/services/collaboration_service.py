"""
Collaboration service for comments, mentions, and activity tracking.

Provides team collaboration features:
- Comments with threading
- @mention detection and notifications
- Emoji reactions
- Activity feed
"""
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.comment import Comment, Reaction, EntityType
from backend.models.activity import Activity, ActivityType
from backend.models.user import User
from backend.services.notifications import NotificationService, NotificationType


class CollaborationService:
    """Service for handling team collaboration features"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    async def add_comment(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
        content: str,
        parent_id: Optional[UUID] = None
    ) -> Comment:
        """
        Add a comment to an entity.
        
        Parses @mentions from content and notifies mentioned users.
        Creates activity entry.
        """
        # Parse @mentions from content
        # Pattern: @username or @email
        mention_pattern = r'@([\w\.\-]+(?:@[\w\.\-]+\.[a-zA-Z]{2,})?)'
        potential_mentions = re.findall(mention_pattern, content)
        
        # Resolve mentions to user UUIDs
        mentioned_user_ids = []
        if potential_mentions:
            # Try to find users by email or name
            for mention in potential_mentions:
                if '@' in mention:  # Email
                    result = await db.execute(
                        select(User).where(
                            and_(
                                User.tenant_id == tenant_id,
                                User.email == mention,
                                User.is_active == True
                            )
                        )
                    )
                else:  # Username/name
                    result = await db.execute(
                        select(User).where(
                            and_(
                                User.tenant_id == tenant_id,
                                User.name.ilike(f"%{mention}%"),
                                User.is_active == True
                            )
                        )
                    )
                user = result.scalar_one_or_none()
                if user and user.id not in mentioned_user_ids:
                    mentioned_user_ids.append(str(user.id))
        
        # Create comment
        comment = Comment(
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            content=content,
            parent_id=parent_id,
            mentions=mentioned_user_ids
        )
        db.add(comment)
        await db.flush()
        
        # Get comment author for notifications
        author_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        author = author_result.scalar_one()
        
        # Create activity
        await self.record_activity(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            activity_type=ActivityType.COMMENT_ADDED,
            entity_type=entity_type.value,
            entity_id=entity_id,
            title=f"{author.name} commented on {entity_type.value}",
            details={
                "comment_id": str(comment.id),
                "content_preview": content[:100]
            }
        )
        
        # Notify mentioned users
        for mentioned_id in mentioned_user_ids:
            await self.record_activity(
                db=db,
                tenant_id=tenant_id,
                user_id=UUID(mentioned_id),
                activity_type=ActivityType.USER_MENTIONED,
                entity_type=entity_type.value,
                entity_id=entity_id,
                title=f"{author.name} mentioned you in a comment",
                details={
                    "comment_id": str(comment.id),
                    "content_preview": content[:100]
                }
            )
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    async def edit_comment(
        self,
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID,
        new_content: str
    ) -> Comment:
        """
        Edit a comment (only by the author).
        
        Marks comment as edited.
        """
        result = await db.execute(
            select(Comment).where(
                and_(
                    Comment.id == comment_id,
                    Comment.user_id == user_id,
                    Comment.is_deleted == False
                )
            )
        )
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise ValueError("Comment not found or you don't have permission to edit it")
        
        comment.content = new_content
        comment.is_edited = True
        comment.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    async def delete_comment(
        self,
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> Comment:
        """
        Soft delete a comment.
        
        Only comment author or admin can delete.
        """
        query = select(Comment).where(Comment.id == comment_id)
        
        if not is_admin:
            query = query.where(Comment.user_id == user_id)
        
        result = await db.execute(query)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise ValueError("Comment not found or you don't have permission to delete it")
        
        comment.is_deleted = True
        comment.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    async def get_comments(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        entity_id: UUID,
        tenant_id: UUID,
        include_deleted: bool = False
    ) -> List[Comment]:
        """
        Get comments for an entity with nested replies.
        
        Returns top-level comments with their replies loaded.
        """
        query = select(Comment).where(
            and_(
                Comment.tenant_id == tenant_id,
                Comment.entity_type == entity_type,
                Comment.entity_id == entity_id,
                Comment.parent_id == None  # Top-level comments only
            )
        )
        
        if not include_deleted:
            query = query.where(Comment.is_deleted == False)
        
        query = query.options(
            selectinload(Comment.replies),
            selectinload(Comment.user),
            selectinload(Comment.reactions)
        ).order_by(Comment.created_at.asc())
        
        result = await db.execute(query)
        comments = result.scalars().all()
        
        return comments
    
    async def add_reaction(
        self,
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID,
        emoji: str
    ) -> Optional[Reaction]:
        """
        Add or toggle a reaction to a comment.
        
        If user already has this reaction, remove it (toggle).
        Otherwise, add the reaction.
        """
        # Check if reaction already exists
        result = await db.execute(
            select(Reaction).where(
                and_(
                    Reaction.comment_id == comment_id,
                    Reaction.user_id == user_id,
                    Reaction.emoji == emoji
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Toggle: remove reaction
            await db.delete(existing)
            await db.commit()
            return None
        else:
            # Add new reaction
            reaction = Reaction(
                comment_id=comment_id,
                user_id=user_id,
                emoji=emoji
            )
            db.add(reaction)
            await db.commit()
            await db.refresh(reaction)
            return reaction
    
    async def record_activity(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        activity_type: ActivityType,
        entity_type: str,
        entity_id: UUID,
        title: str,
        user_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Activity:
        """
        Record an activity entry.
        
        Used for activity feed and notifications.
        """
        activity = Activity(
            tenant_id=tenant_id,
            user_id=user_id,
            activity_type=activity_type,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            details=details or {}
        )
        db.add(activity)
        await db.flush()
        
        return activity
    
    async def get_activity_feed(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        activity_types: Optional[List[ActivityType]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get activity feed with pagination.
        
        Optionally filter by user_id (activities for a specific user).
        """
        query = select(Activity).where(Activity.tenant_id == tenant_id)
        
        if user_id:
            query = query.where(Activity.user_id == user_id)
        
        if activity_types:
            query = query.where(Activity.activity_type.in_(activity_types))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.options(selectinload(Activity.user)).order_by(
            Activity.created_at.desc()
        ).offset(offset).limit(limit)
        
        result = await db.execute(query)
        activities = result.scalars().all()
        
        return {
            "items": [a.to_dict() for a in activities],
            "total": total,
            "offset": offset,
            "limit": limit
        }
    
    async def get_unread_count(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID
    ) -> int:
        """
        Get count of unread activities for a user.
        """
        result = await db.execute(
            select(func.count()).select_from(Activity).where(
                and_(
                    Activity.tenant_id == tenant_id,
                    Activity.user_id == user_id,
                    Activity.is_read == False
                )
            )
        )
        count = result.scalar()
        return count
    
    async def mark_as_read(
        self,
        db: AsyncSession,
        activity_ids: List[UUID],
        user_id: UUID
    ) -> int:
        """
        Mark activities as read.
        
        Returns count of activities marked as read.
        """
        # Only mark activities that belong to the user
        result = await db.execute(
            select(Activity).where(
                and_(
                    Activity.id.in_(activity_ids),
                    Activity.user_id == user_id,
                    Activity.is_read == False
                )
            )
        )
        activities = result.scalars().all()
        
        for activity in activities:
            activity.is_read = True
        
        await db.commit()
        
        return len(activities)
