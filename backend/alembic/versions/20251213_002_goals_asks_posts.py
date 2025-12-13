"""Add goals, asks, and posts tables

Revision ID: 002_goals_asks_posts
Revises: 001_initial
Create Date: 2025-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_goals_asks_posts'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create goals, asks, and posts tables"""

    # Create GoalType enum
    goal_type_enum = postgresql.ENUM('fundraising', 'hiring', 'growth', 'partnerships', 'learning', name='goaltype')
    goal_type_enum.create(op.get_bind(), checkfirst=True)

    # Create goals table
    op.create_table(
        'goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('fundraising', 'hiring', 'growth', 'partnerships', 'learning', name='goaltype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for goals table
    op.create_index('ix_goals_id', 'goals', ['id'])
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    op.create_index('ix_goals_type', 'goals', ['type'])
    op.create_index('ix_goals_is_active', 'goals', ['is_active'])

    # Create AskUrgency and AskStatus enums
    ask_urgency_enum = postgresql.ENUM('low', 'medium', 'high', name='askurgency')
    ask_urgency_enum.create(op.get_bind(), checkfirst=True)

    ask_status_enum = postgresql.ENUM('open', 'fulfilled', 'closed', name='askstatus')
    ask_status_enum.create(op.get_bind(), checkfirst=True)

    # Create asks table
    op.create_table(
        'asks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('urgency', sa.Enum('low', 'medium', 'high', name='askurgency'), nullable=False, server_default='medium'),
        sa.Column('status', sa.Enum('open', 'fulfilled', 'closed', name='askstatus'), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('fulfilled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='SET NULL')
    )

    # Create indexes for asks table
    op.create_index('ix_asks_id', 'asks', ['id'])
    op.create_index('ix_asks_user_id', 'asks', ['user_id'])
    op.create_index('ix_asks_goal_id', 'asks', ['goal_id'])
    op.create_index('ix_asks_urgency', 'asks', ['urgency'])
    op.create_index('ix_asks_status', 'asks', ['status'])

    # Create PostType enum
    post_type_enum = postgresql.ENUM('progress', 'learning', 'milestone', 'ask', name='posttype')
    post_type_enum.create(op.get_bind(), checkfirst=True)

    # Create embedding_status enum
    embedding_status_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='embedding_status_enum')
    embedding_status_enum.create(op.get_bind(), checkfirst=True)

    # Create posts table
    op.create_table(
        'posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('progress', 'learning', 'milestone', 'ask', name='posttype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_cross_posted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('embedding_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='embedding_status_enum'), nullable=False, server_default='pending'),
        sa.Column('embedding_created_at', sa.DateTime(), nullable=True),
        sa.Column('embedding_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for posts table
    op.create_index('ix_posts_id', 'posts', ['id'])
    op.create_index('ix_posts_user_id', 'posts', ['user_id'])
    op.create_index('ix_posts_type', 'posts', ['type'])
    op.create_index('ix_posts_created_at', 'posts', ['created_at'])


def downgrade() -> None:
    """Drop tables and enums"""
    op.drop_index('ix_posts_created_at', 'posts')
    op.drop_index('ix_posts_type', 'posts')
    op.drop_index('ix_posts_user_id', 'posts')
    op.drop_index('ix_posts_id', 'posts')
    op.drop_table('posts')

    op.drop_index('ix_asks_status', 'asks')
    op.drop_index('ix_asks_urgency', 'asks')
    op.drop_index('ix_asks_goal_id', 'asks')
    op.drop_index('ix_asks_user_id', 'asks')
    op.drop_index('ix_asks_id', 'asks')
    op.drop_table('asks')

    op.drop_index('ix_goals_is_active', 'goals')
    op.drop_index('ix_goals_type', 'goals')
    op.drop_index('ix_goals_user_id', 'goals')
    op.drop_index('ix_goals_id', 'goals')
    op.drop_table('goals')

    # Drop enums
    sa.Enum(name='embedding_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='posttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='askstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='askurgency').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='goaltype').drop(op.get_bind(), checkfirst=True)
