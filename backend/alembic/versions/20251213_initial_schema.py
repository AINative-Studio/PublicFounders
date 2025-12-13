"""Initial schema for users and founder_profiles

Revision ID: 001_initial
Revises:
Create Date: 2025-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users and founder_profiles tables"""

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('linkedin_id', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('headline', sa.String(500), nullable=True),
        sa.Column('profile_photo_url', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True, unique=True),
        sa.Column('phone_number', sa.String(20), nullable=True, unique=True),
        sa.Column('phone_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('phone_verification_code', sa.String(10), nullable=True),
        sa.Column('phone_verification_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True)
    )

    # Create indexes for users table
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_linkedin_id', 'users', ['linkedin_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_phone_number', 'users', ['phone_number'])

    # Create founder_profiles table
    op.create_table(
        'founder_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('current_focus', sa.Text(), nullable=True),
        sa.Column('autonomy_mode', sa.Enum('suggest', 'approve', 'auto', name='autonomymode'),
                  nullable=False, server_default='suggest'),
        sa.Column('public_visibility', sa.Boolean(), nullable=False, default=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('embedding_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create index for founder_profiles
    op.create_index('ix_founder_profiles_embedding_id', 'founder_profiles', ['embedding_id'])


def downgrade() -> None:
    """Drop tables"""
    op.drop_index('ix_founder_profiles_embedding_id', 'founder_profiles')
    op.drop_table('founder_profiles')

    op.drop_index('ix_users_phone_number', 'users')
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_linkedin_id', 'users')
    op.drop_index('ix_users_id', 'users')
    op.drop_table('users')

    # Drop enum type
    sa.Enum(name='autonomymode').drop(op.get_bind(), checkfirst=True)
