"""Add introductions and interaction_outcomes tables

Revision ID: 004_introductions_outcomes
Revises: 003_companies_roles
Create Date: 2025-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_introductions_outcomes'
down_revision: Union[str, None] = '003_companies_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create introductions and interaction_outcomes tables"""

    # Create IntroductionChannel enum
    intro_channel_enum = postgresql.ENUM('linkedin', 'sms', 'email', name='introductionchannel')
    intro_channel_enum.create(op.get_bind(), checkfirst=True)

    # Create IntroductionStatus enum
    intro_status_enum = postgresql.ENUM(
        'proposed', 'sent', 'accepted', 'declined', 'successful', 'failed',
        name='introductionstatus'
    )
    intro_status_enum.create(op.get_bind(), checkfirst=True)

    # Create introductions table
    op.create_table(
        'introductions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_initiated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('channel', sa.Enum('linkedin', 'sms', 'email', name='introductionchannel'), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('proposed', 'sent', 'accepted', 'declined', 'successful', 'failed', name='introductionstatus'), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('embedding_updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for introductions table
    op.create_index('ix_introductions_id', 'introductions', ['id'])
    op.create_index('ix_introductions_requester_id', 'introductions', ['requester_id'])
    op.create_index('ix_introductions_target_id', 'introductions', ['target_id'])
    op.create_index('ix_introductions_agent_initiated', 'introductions', ['agent_initiated'])
    op.create_index('ix_introductions_channel', 'introductions', ['channel'])
    op.create_index('ix_introductions_status', 'introductions', ['status'])
    op.create_index('ix_introductions_embedding_id', 'introductions', ['embedding_id'])

    # Create OutcomeType enum
    outcome_type_enum = postgresql.ENUM('meeting', 'investment', 'hire', 'partnership', 'none', name='outcometype')
    outcome_type_enum.create(op.get_bind(), checkfirst=True)

    # Create interaction_outcomes table
    op.create_table(
        'interaction_outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('introduction_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('outcome_type', sa.Enum('meeting', 'investment', 'hire', 'partnership', 'none', name='outcometype'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('embedding_updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['introduction_id'], ['introductions.id'], ondelete='CASCADE')
    )

    # Create indexes for interaction_outcomes table
    op.create_index('ix_interaction_outcomes_id', 'interaction_outcomes', ['id'])
    op.create_index('ix_interaction_outcomes_introduction_id', 'interaction_outcomes', ['introduction_id'])
    op.create_index('ix_interaction_outcomes_outcome_type', 'interaction_outcomes', ['outcome_type'])
    op.create_index('ix_interaction_outcomes_embedding_id', 'interaction_outcomes', ['embedding_id'])


def downgrade() -> None:
    """Drop tables and enums"""
    op.drop_index('ix_interaction_outcomes_embedding_id', 'interaction_outcomes')
    op.drop_index('ix_interaction_outcomes_outcome_type', 'interaction_outcomes')
    op.drop_index('ix_interaction_outcomes_introduction_id', 'interaction_outcomes')
    op.drop_index('ix_interaction_outcomes_id', 'interaction_outcomes')
    op.drop_table('interaction_outcomes')

    op.drop_index('ix_introductions_embedding_id', 'introductions')
    op.drop_index('ix_introductions_status', 'introductions')
    op.drop_index('ix_introductions_channel', 'introductions')
    op.drop_index('ix_introductions_agent_initiated', 'introductions')
    op.drop_index('ix_introductions_target_id', 'introductions')
    op.drop_index('ix_introductions_requester_id', 'introductions')
    op.drop_index('ix_introductions_id', 'introductions')
    op.drop_table('introductions')

    # Drop enums
    sa.Enum(name='outcometype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='introductionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='introductionchannel').drop(op.get_bind(), checkfirst=True)
