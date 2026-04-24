"""
Tag API endpoints.

Provides CRUD operations for tags, autocomplete suggestions, and namespace management.
"""
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.models.tag import Tag
from backend.models.tenant import Tenant
from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant


router = APIRouter()


# Pydantic schemas
class TagCreate(BaseModel):
    name: str
    namespace: str
    description: Optional[str] = None
    color: Optional[str] = None
    aliases: Optional[List[str]] = None


class TagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    aliases: Optional[List[str]] = None


class TagMerge(BaseModel):
    source_id: UUID
    target_id: UUID


class TagResponse(BaseModel):
    id: UUID
    name: str
    namespace: str
    display_name: Optional[str]
    description: Optional[str]
    color: Optional[str]
    aliases: List[str]
    usage_count: int
    is_default: bool
    is_system: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=Dict[str, Any])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    search: Optional[str] = Query(None, description="Search in name, display_name, aliases"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> Dict[str, Any]:
    """
    List all tags for tenant, optionally grouped by namespace.
    
    Returns tags with filtering and search capabilities.
    """
    # Build base query
    conditions = [Tag.tenant_id == tenant.id]
    
    if namespace:
        conditions.append(Tag.namespace == namespace)
    
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Tag.name.ilike(search_pattern),
                Tag.display_name.ilike(search_pattern),
                func.cast(Tag.aliases, db.Text).ilike(search_pattern),
            )
        )
    
    stmt = select(Tag).where(and_(*conditions)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tags = result.scalars().all()
    
    # Get total count
    count_stmt = select(func.count(Tag.id)).where(and_(*conditions))
    total = await db.scalar(count_stmt)
    
    # Group by namespace
    grouped = {}
    for tag in tags:
        if tag.namespace not in grouped:
            grouped[tag.namespace] = []
        grouped[tag.namespace].append(TagResponse.model_validate(tag))
    
    return {
        "tags": [TagResponse.model_validate(tag) for tag in tags],
        "grouped": grouped,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/suggest", response_model=List[TagResponse])
async def suggest_tags(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    q: str = Query(..., description="Query string for autocomplete"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    limit: int = Query(10, le=50),
) -> List[TagResponse]:
    """
    Autocomplete endpoint for tag suggestions.
    
    Fuzzy matches across name, display_name, and aliases.
    Returns results sorted by usage_count desc.
    """
    conditions = [Tag.tenant_id == tenant.id]
    
    if namespace:
        conditions.append(Tag.namespace == namespace)
    
    # Fuzzy match
    search_pattern = f"%{q}%"
    conditions.append(
        or_(
            Tag.name.ilike(search_pattern),
            Tag.display_name.ilike(search_pattern),
            func.cast(Tag.aliases, db.Text).ilike(search_pattern),
        )
    )
    
    stmt = (
        select(Tag)
        .where(and_(*conditions))
        .order_by(Tag.usage_count.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    tags = result.scalars().all()
    
    return [TagResponse.model_validate(tag) for tag in tags]


@router.get("/namespaces", response_model=Dict[str, int])
async def list_namespaces(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, int]:
    """
    List available namespaces with tag counts.
    
    Returns a mapping of namespace -> count.
    """
    stmt = (
        select(Tag.namespace, func.count(Tag.id))
        .where(Tag.tenant_id == tenant.id)
        .group_by(Tag.namespace)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return {namespace: count for namespace, count in rows}


@router.post("", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> TagResponse:
    """
    Create a new tag.
    
    Requires namespace and name. Display name defaults to namespace:name.
    """
    # Check for duplicate
    stmt = select(Tag).where(
        and_(
            Tag.tenant_id == tenant.id,
            Tag.namespace == tag_data.namespace,
            Tag.name == tag_data.name,
        )
    )
    existing = await db.scalar(stmt)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Tag {tag_data.namespace}:{tag_data.name} already exists"
        )
    
    # Create tag
    tag = Tag(
        tenant_id=tenant.id,
        name=tag_data.name,
        namespace=tag_data.namespace,
        display_name=f"{tag_data.namespace}:{tag_data.name}",
        description=tag_data.description,
        color=tag_data.color,
        aliases=tag_data.aliases or [],
    )
    
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    tag_data: TagUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> TagResponse:
    """
    Update an existing tag.
    
    Can update name, description, color, and aliases.
    """
    stmt = select(Tag).where(and_(Tag.id == tag_id, Tag.tenant_id == tenant.id))
    tag = await db.scalar(stmt)
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Update fields
    if tag_data.name is not None:
        tag.name = tag_data.name
        tag.display_name = f"{tag.namespace}:{tag.name}"
    
    if tag_data.description is not None:
        tag.description = tag_data.description
    
    if tag_data.color is not None:
        tag.color = tag_data.color
    
    if tag_data.aliases is not None:
        tag.aliases = tag_data.aliases
    
    tag.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(tag)
    
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Delete a tag.
    
    Cannot delete system tags. Warns if usage_count > 0.
    """
    stmt = select(Tag).where(and_(Tag.id == tag_id, Tag.tenant_id == tenant.id))
    tag = await db.scalar(stmt)
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag.is_system:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete system tags. Consider disabling instead."
        )
    
    if tag.usage_count > 0:
        # Warning but allow deletion
        pass
    
    await db.delete(tag)
    await db.commit()
    
    return {"status": "deleted", "id": str(tag_id)}


@router.post("/merge")
async def merge_tags(
    merge_data: TagMerge,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, str]:
    """
    Merge source tag into target tag.
    
    Moves source name to target aliases, updates all entity references, deletes source.
    """
    # Load both tags
    stmt = select(Tag).where(
        and_(
            Tag.id.in_([merge_data.source_id, merge_data.target_id]),
            Tag.tenant_id == tenant.id,
        )
    )
    result = await db.execute(stmt)
    tags = {str(tag.id): tag for tag in result.scalars().all()}
    
    source = tags.get(str(merge_data.source_id))
    target = tags.get(str(merge_data.target_id))
    
    if not source or not target:
        raise HTTPException(status_code=404, detail="One or both tags not found")
    
    # Add source name to target aliases if not already present
    if source.name not in target.aliases:
        target.aliases = target.aliases + [source.name]
    
    # Update usage count
    target.usage_count += source.usage_count
    
    # TODO: Update references in assets, bundles, etc.
    # This would require scanning asset.tags JSON fields and updating them
    
    # Delete source
    await db.delete(source)
    await db.commit()
    await db.refresh(target)
    
    return {
        "status": "merged",
        "source_id": str(merge_data.source_id),
        "target_id": str(merge_data.target_id),
    }
