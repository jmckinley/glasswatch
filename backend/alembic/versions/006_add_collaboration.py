"""Add collaboration features (comments, reactions, activity)

Revision ID: 006_add_collaboration
Revises: 002_add_authentication
Create Date: 2026-04-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_collaboration'
down_revision = '002_add_authentication'
branch_labels = None
depends_on = None


def upgrade():
    # Create entity type enum
    op.execute("""
        CREATE TYPE entitytype AS ENUM (
            'asset',
            'vulnerability',
            'bundle',
            'goal',
            'approval'
        )
    """)
    
    # Create activity type enum
    op.execute("""
        CREATE TYPE activitytype AS ENUM (
            'comment_added',
            'approval_requested',
            'approval_approved',
            'approval_rejected',
            'bundle_created',
            'bundle_executed',
            'asset_discovered',
            'vulnerability_found',
            'goal_created',
            'goal_completed',
            'rollback_initiated',
            'scan_completed',
            'user_mentioned'
        )
    """)
    
    # Create comments table
    op.create_table('comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.Enum(
            'asset', 'vulnerability', 'bundle', 'goal', 'approval',
            name='entitytype'
        ), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('mentions', sa.JSON(), nullable=False),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for comments
    op.create_index('idx_comments_entity', 'comments', ['entity_type', 'entity_id'])
    op.create_index('idx_comments_tenant', 'comments', ['tenant_id'])
    op.create_index('idx_comments_user', 'comments', ['user_id'])
    op.create_index('idx_comments_parent', 'comments', ['parent_id'])
    op.create_index('idx_comments_created', 'comments', ['created_at'])
    
    # Create reactions table
    op.create_table('reactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emoji', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('comment_id', 'user_id', 'emoji', name='uq_reaction_user_emoji')
    )
    
    # Create indexes for reactions
    op.create_index('idx_reactions_comment', 'reactions', ['comment_id'])
    op.create_index('idx_reactions_user', 'reactions', ['user_id'])
    
    # Create activities table
    op.create_table('activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('activity_type', sa.Enum(
            'comment_added', 'approval_requested', 'approval_approved', 'approval_rejected',
            'bundle_created', 'bundle_executed', 'asset_discovered', 'vulnerability_found',
            'goal_created', 'goal_completed', 'rollback_initiated', 'scan_completed',
            'user_mentioned',
            name='activitytype'
        ), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for activities
    op.create_index('idx_activities_tenant', 'activities', ['tenant_id'])
    op.create_index('idx_activities_user', 'activities', ['user_id'])
    op.create_index('idx_activities_type', 'activities', ['activity_type'])
    op.create_index('idx_activities_entity', 'activities', ['entity_type', 'entity_id'])
    op.create_index('idx_activities_created', 'activities', ['created_at'])
    op.create_index('idx_activities_unread', 'activities', ['user_id', 'is_read'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_activities_unread', table_name='activities')
    op.drop_index('idx_activities_created', table_name='activities')
    op.drop_index('idx_activities_entity', table_name='activities')
    op.drop_index('idx_activities_type', table_name='activities')
    op.drop_index('idx_activities_user', table_name='activities')
    op.drop_index('idx_activities_tenant', table_name='activities')
    
    op.drop_index('idx_reactions_user', table_name='reactions')
    op.drop_index('idx_reactions_comment', table_name='reactions')
    
    op.drop_index('idx_comments_created', table_name='comments')
    op.drop_index('idx_comments_parent', table_name='comments')
    op.drop_index('idx_comments_user', table_name='comments')
    op.drop_index('idx_comments_tenant', table_name='comments')
    op.drop_index('idx_comments_entity', table_name='comments')
    
    # Drop tables
    op.drop_table('activities')
    op.drop_table('reactions')
    op.drop_table('comments')
    
    # Drop enums
    op.execute("DROP TYPE activitytype")
    op.execute("DROP TYPE entitytype")
