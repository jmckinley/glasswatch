"""
Comment API endpoints.

Manages comments, mentions, and reactions on entities.
"""
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.comment import Comment, Reaction, EntityType
from backend.models.tenant import Tenant
from backend.models.user import User, UserRole
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant, get_current_user
from backend.services.collaboration_service import CollaborationService


router = APIRouter()
collab_service = CollaborationService()


# Pydantic schemas
class CommentCreate(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    parent_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ReactionCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=20)


@router.post("/", status_code=201)
async def add_comment(
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Add a comment to an entity.
    
    Supports:
    - Top-level comments
    - Threaded replies (via parent_id)
    - @mentions (will notify mentioned users)
    """
    try:
        comment = await collab_service.add_comment(
            db=db,
            tenant_id=tenant.id,
            user_id=user.id,
            entity_type=comment_data.entity_type,
            entity_id=comment_data.entity_id,
            content=comment_data.content,
            parent_id=comment_data.parent_id
        )
        
        return comment.to_dict()
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_comments(
    entity_type: EntityType = Query(..., description="Entity type"),
    entity_id: UUID = Query(..., description="Entity ID"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List comments for an entity.
    
    Returns top-level comments with nested replies.
    """
    comments = await collab_service.get_comments(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant.id
    )
    
    # Convert to dict with nested structure
    items = []
    for comment in comments:
        comment_dict = comment.to_dict()
        
        # Add user info
        comment_dict["user"] = {
            "id": str(comment.user.id),
            "name": comment.user.name,
            "email": comment.user.email,
            "avatar_url": comment.user.avatar_url
        }
        
        # Add replies
        comment_dict["replies"] = []
        for reply in comment.replies:
            if not reply.is_deleted:
                reply_dict = reply.to_dict()
                reply_dict["user"] = {
                    "id": str(reply.user.id),
                    "name": reply.user.name,
                    "email": reply.user.email,
                    "avatar_url": reply.user.avatar_url
                }
                reply_dict["reactions"] = [r.to_dict() for r in reply.reactions]
                comment_dict["replies"].append(reply_dict)
        
        # Add reactions
        comment_dict["reactions"] = [r.to_dict() for r in comment.reactions]
        
        items.append(comment_dict)
    
    return {
        "items": items,
        "total": len(items)
    }


@router.get("/{comment_id}")
async def get_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get a specific comment with replies.
    """
    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.tenant_id == tenant.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment_dict = comment.to_dict()
    comment_dict["user"] = {
        "id": str(comment.user.id),
        "name": comment.user.name,
        "email": comment.user.email,
        "avatar_url": comment.user.avatar_url
    }
    
    # Add replies
    comment_dict["replies"] = []
    for reply in comment.replies:
        if not reply.is_deleted:
            reply_dict = reply.to_dict()
            reply_dict["user"] = {
                "id": str(reply.user.id),
                "name": reply.user.name,
                "email": reply.user.email,
                "avatar_url": reply.user.avatar_url
            }
            comment_dict["replies"].append(reply_dict)
    
    # Add reactions
    comment_dict["reactions"] = [r.to_dict() for r in comment.reactions]
    
    return comment_dict


@router.patch("/{comment_id}")
async def edit_comment(
    comment_id: UUID,
    comment_data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Edit a comment (only by author).
    """
    try:
        comment = await collab_service.edit_comment(
            db=db,
            comment_id=comment_id,
            user_id=user.id,
            new_content=comment_data.content
        )
        
        return comment.to_dict()
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Soft delete a comment.
    
    Only the comment author or admin can delete.
    """
    try:
        is_admin = user.role == UserRole.ADMIN
        
        await collab_service.delete_comment(
            db=db,
            comment_id=comment_id,
            user_id=user.id,
            is_admin=is_admin
        )
        
        return {"success": True, "message": "Comment deleted"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{comment_id}/reactions")
async def add_reaction(
    comment_id: UUID,
    reaction_data: ReactionCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Add or toggle a reaction to a comment.
    
    If you already have this reaction, it will be removed (toggle).
    """
    # Verify comment exists and belongs to tenant
    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.tenant_id == tenant.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    reaction = await collab_service.add_reaction(
        db=db,
        comment_id=comment_id,
        user_id=user.id,
        emoji=reaction_data.emoji
    )
    
    if reaction:
        return {"action": "added", "reaction": reaction.to_dict()}
    else:
        return {"action": "removed", "emoji": reaction_data.emoji}


@router.get("/{comment_id}/reactions")
async def list_reactions(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List all reactions for a comment.
    
    Groups reactions by emoji with counts.
    """
    # Verify comment exists and belongs to tenant
    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.tenant_id == tenant.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Get all reactions
    result = await db.execute(
        select(Reaction).where(Reaction.comment_id == comment_id)
    )
    reactions = result.scalars().all()
    
    # Group by emoji
    grouped = {}
    for reaction in reactions:
        if reaction.emoji not in grouped:
            grouped[reaction.emoji] = {
                "emoji": reaction.emoji,
                "count": 0,
                "users": []
            }
        grouped[reaction.emoji]["count"] += 1
        grouped[reaction.emoji]["users"].append({
            "id": str(reaction.user_id),
            "name": reaction.user.name if hasattr(reaction, 'user') else None
        })
    
    return {
        "reactions": list(grouped.values()),
        "total": len(reactions)
    }
