"""
Team Invite API endpoints.

Handles:
- Creating invitations (admin only)
- Listing pending invitations
- Revoking invitations
- Accepting invitations (public endpoint)
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth_workos import create_access_token, get_current_user
from backend.db.session import get_db
from backend.models.invite import Invite
from backend.models.user import User, UserRole

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VALID_ROLES = {"viewer", "analyst", "operator", "admin"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CreateInviteRequest(BaseModel):
    email: EmailStr
    role: str = "analyst"


class InviteResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
    created_by: Optional[str]
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class AcceptInviteResponse(BaseModel):
    access_token: str
    user: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


async def _send_invite_email(
    to_email: str,
    inviter_name: str,
    invite_url: str,
) -> None:
    """Send invite email via Resend (lazy import, fire-and-forget)."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print(f"[Invites] No RESEND_API_KEY configured — skipping invite email to {to_email}")
        return

    from_address = os.environ.get("EMAIL_FROM", "noreply@updates.mckinleylabsllc.com")

    html_body = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; background: #111; color: #fff; padding: 40px; border-radius: 8px;">
  <h1 style="color: #fff;">You've been invited to Glasswatch</h1>
  <p style="color: #aaa;">{inviter_name} has invited you to join their team on Glasswatch — the AI-driven patch management platform.</p>
  <a href="{invite_url}" style="display: inline-block; background: #6366f1; color: #fff; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin: 20px 0;">Accept Invitation</a>
  <p style="color: #666; font-size: 12px;">This invitation expires in 7 days. If you didn't expect this, ignore it.</p>
</div>
"""

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_address,
                    "to": [to_email],
                    "subject": "You've been invited to Glasswatch",
                    "html": html_body,
                },
                timeout=15.0,
            )
        if response.status_code not in (200, 201):
            print(f"[Invites] Resend returned {response.status_code}: {response.text}")
    except Exception as exc:
        print(f"[Invites] Failed to send invite email: {exc}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/invites", response_model=InviteResponse, status_code=201)
async def create_invite(
    body: CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a team invitation (admin only).
    Sends an email to the invitee with a one-time token link.
    """
    role = body.role.lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    invite = Invite(
        tenant_id=current_user.tenant_id,
        email=body.email,
        role=role,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
        accepted_at=None,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    invite_url = f"{frontend_url}/invite/accept?token={token}"

    await _send_invite_email(
        to_email=body.email,
        inviter_name=current_user.name,
        invite_url=invite_url,
    )

    return InviteResponse(
        id=str(invite.id),
        tenant_id=str(invite.tenant_id),
        email=invite.email,
        role=invite.role,
        created_by=str(invite.created_by) if invite.created_by else None,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        created_at=invite.created_at,
    )


@router.get("/invites", response_model=List[InviteResponse])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List pending (not accepted, not expired) invites for the current tenant.
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(Invite).where(
            and_(
                Invite.tenant_id == current_user.tenant_id,
                Invite.accepted_at.is_(None),
                Invite.expires_at > now,
            )
        ).order_by(Invite.created_at.desc())
    )
    invites = result.scalars().all()

    return [
        InviteResponse(
            id=str(i.id),
            tenant_id=str(i.tenant_id),
            email=i.email,
            role=i.role,
            created_by=str(i.created_by) if i.created_by else None,
            expires_at=i.expires_at,
            accepted_at=i.accepted_at,
            created_at=i.created_at,
        )
        for i in invites
    ]


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Revoke (delete) a pending invitation.
    """
    result = await db.execute(
        select(Invite).where(
            and_(
                Invite.id == invite_id,
                Invite.tenant_id == current_user.tenant_id,
            )
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    await db.delete(invite)
    await db.commit()
    return {"detail": "Invite revoked"}


@router.post("/invites/accept", response_model=AcceptInviteResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a team invitation.
    Public endpoint — no auth required.
    Creates the user and marks the invite as accepted.
    """
    now = datetime.utcnow()

    # Look up invite
    result = await db.execute(
        select(Invite).where(Invite.token == body.token)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or already used")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")
    if invite.expires_at < now:
        raise HTTPException(status_code=400, detail="Invite has expired")

    # Check email isn't already registered in this tenant
    existing = await db.execute(
        select(User).where(
            and_(User.email == invite.email, User.tenant_id == invite.tenant_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists in this team")

    # Map invite role to UserRole enum
    role_map = {
        "admin": UserRole.ADMIN,
        "operator": UserRole.ENGINEER,
        "analyst": UserRole.ENGINEER,
        "viewer": UserRole.VIEWER,
    }
    user_role = role_map.get(invite.role.lower(), UserRole.VIEWER)

    # Hash the password
    password_hash = pwd_context.hash(body.password)

    # Create user
    user = User(
        tenant_id=invite.tenant_id,
        email=invite.email,
        name=body.name,
        role=user_role,
        password_hash=password_hash,
        is_active=True,
        permissions={},
        preferences={},
    )
    db.add(user)

    # Mark invite accepted
    invite.accepted_at = now
    await db.commit()
    await db.refresh(user)

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return AcceptInviteResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id),
        },
    )
