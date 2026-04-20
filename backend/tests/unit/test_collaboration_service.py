"""
Unit tests for the collaboration service.

Tests comments, @mentions, threading, reactions, and activity feed.
"""
import pytest
from uuid import uuid4

from backend.services.collaboration_service import CollaborationService
from backend.models.comment import EntityType, Reaction
from backend.models.activity import ActivityType


pytestmark = pytest.mark.asyncio


class TestCollaborationService:
    """Test suite for CollaborationService"""
    
    async def test_add_comment(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test adding a comment to an entity"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="This bundle looks good to deploy"
        )
        
        assert comment is not None
        assert comment.user_id == test_user.id
        assert comment.entity_type == EntityType.BUNDLE
        assert comment.entity_id == bundle.id
        assert comment.content == "This bundle looks good to deploy"
    
    async def test_mention_parsing_email(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test @mention parsing with email addresses"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content=f"Hey @{admin_user.email}, can you review this?"
        )
        
        assert comment is not None
        assert len(comment.mentions) > 0
        # Should have parsed the mention
        assert str(admin_user.id) in comment.mentions or admin_user.email in str(comment.mentions)
    
    async def test_mention_parsing_username(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test @mention parsing with username"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Create user with specific name
        from backend.models.user import User, UserRole
        mentioned_user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="mentioned@example.com",
            name="John Doe",
            role=UserRole.ENGINEER,
            workos_user_id=f"workos_{uuid4()}"
        )
        test_session.add(mentioned_user)
        await test_session.flush()
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="@John please check this out"
        )
        
        assert comment is not None
        # Should attempt to parse the mention
        assert comment.mentions is not None
    
    async def test_threaded_replies(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test threaded comment replies"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # Parent comment
        parent = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Should we deploy this bundle?"
        )
        
        # Reply to parent
        reply = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=admin_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Yes, looks safe to me",
            parent_id=parent.id
        )
        
        assert reply is not None
        assert reply.parent_id == parent.id
    
    async def test_edit_own_comment(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test editing your own comment"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Original content"
        )
        
        # Edit the comment
        edited = await service.edit_comment(
            db=test_session,
            comment_id=comment.id,
            user_id=test_user.id,
            new_content="Edited content"
        )
        
        assert edited.content == "Edited content"
        assert edited.edited_at is not None
    
    async def test_cannot_edit_others_comment(
        self, test_session, test_tenant, test_user, admin_user, create_test_bundle
    ):
        """Test that you cannot edit someone else's comment"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        # User creates comment
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Original content"
        )
        
        # Admin tries to edit user's comment (should fail)
        with pytest.raises(PermissionError, match="not authorized|permission|owner"):
            await service.edit_comment(
                db=test_session,
                comment_id=comment.id,
                user_id=admin_user.id,
                new_content="Hacked content"
            )
    
    async def test_delete_own_comment(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test deleting your own comment"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="To be deleted"
        )
        
        # Delete the comment
        await service.delete_comment(
            db=test_session,
            comment_id=comment.id,
            user_id=test_user.id
        )
        
        # Comment should be marked as deleted
        await test_session.refresh(comment)
        assert comment.deleted_at is not None
    
    async def test_add_reaction(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test adding emoji reaction to comment"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Great work!"
        )
        
        # Add reaction
        reaction = await service.add_reaction(
            db=test_session,
            comment_id=comment.id,
            user_id=test_user.id,
            emoji="👍"
        )
        
        assert reaction is not None
        assert reaction.comment_id == comment.id
        assert reaction.user_id == test_user.id
        assert reaction.emoji == "👍"
    
    async def test_toggle_reaction(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test toggling reaction (add, then remove)"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Test comment"
        )
        
        # Add reaction
        reaction = await service.add_reaction(
            db=test_session,
            comment_id=comment.id,
            user_id=test_user.id,
            emoji="❤️"
        )
        assert reaction is not None
        
        # Remove reaction (toggle off)
        removed = await service.remove_reaction(
            db=test_session,
            comment_id=comment.id,
            user_id=test_user.id,
            emoji="❤️"
        )
        assert removed is True
    
    async def test_activity_feed_created(
        self, test_session, test_tenant, test_user, create_test_bundle
    ):
        """Test that activity entries are created for comments"""
        service = CollaborationService()
        bundle = await create_test_bundle(tenant_id=str(test_tenant.id))
        
        comment = await service.add_comment(
            db=test_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id,
            content="Activity test"
        )
        
        # Get activity feed
        activities = await service.get_activity_feed(
            db=test_session,
            tenant_id=test_tenant.id,
            entity_type=EntityType.BUNDLE,
            entity_id=bundle.id
        )
        
        assert len(activities) > 0
        # Should have activity for comment creation
        comment_activities = [
            a for a in activities 
            if a.activity_type == ActivityType.COMMENT_ADDED
        ]
        assert len(comment_activities) > 0
