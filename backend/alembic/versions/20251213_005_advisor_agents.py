"""Add advisor_agents and agent_memories tables

Revision ID: 005_advisor_agents
Revises: 004_introductions_outcomes
Create Date: 2025-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_advisor_agents'
down_revision: Union[str, None] = '004_introductions_outcomes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create advisor_agents and agent_memories tables"""

    # Create AgentStatus enum
    agent_status_enum = postgresql.ENUM(
        'initializing', 'active', 'paused', 'deactivated',
        name='agentstatus'
    )
    agent_status_enum.create(op.get_bind(), checkfirst=True)

    # Create MemoryType enum
    memory_type_enum = postgresql.ENUM(
        'preference', 'outcome', 'context',
        name='memorytype'
    )
    memory_type_enum.create(op.get_bind(), checkfirst=True)

    # Create advisor_agents table
    op.create_table(
        'advisor_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('status', sa.Enum('initializing', 'active', 'paused', 'deactivated', name='agentstatus'), nullable=False, server_default='initializing'),
        sa.Column('name', sa.String(255), nullable=False, server_default='Advisor'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('memory_namespace', sa.String(255), nullable=True),
        sa.Column('total_memories', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_memory_at', sa.DateTime(), nullable=True),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
        sa.Column('last_summary_at', sa.DateTime(), nullable=True),
        sa.Column('total_suggestions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_actions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for advisor_agents table
    op.create_index('ix_advisor_agents_id', 'advisor_agents', ['id'])
    op.create_index('ix_advisor_agents_user_id', 'advisor_agents', ['user_id'])
    op.create_index('ix_advisor_agents_status', 'advisor_agents', ['status'])

    # Create agent_memories table
    op.create_table(
        'agent_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_type', sa.Enum('preference', 'outcome', 'context', name='memorytype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['advisor_agents.id'], ondelete='CASCADE')
    )

    # Create indexes for agent_memories table
    op.create_index('ix_agent_memories_id', 'agent_memories', ['id'])
    op.create_index('ix_agent_memories_agent_id', 'agent_memories', ['agent_id'])
    op.create_index('ix_agent_memories_memory_type', 'agent_memories', ['memory_type'])
    op.create_index('ix_agent_memories_embedding_id', 'agent_memories', ['embedding_id'])


def downgrade() -> None:
    """Drop tables and enums"""
    op.drop_index('ix_agent_memories_embedding_id', 'agent_memories')
    op.drop_index('ix_agent_memories_memory_type', 'agent_memories')
    op.drop_index('ix_agent_memories_agent_id', 'agent_memories')
    op.drop_index('ix_agent_memories_id', 'agent_memories')
    op.drop_table('agent_memories')

    op.drop_index('ix_advisor_agents_status', 'advisor_agents')
    op.drop_index('ix_advisor_agents_user_id', 'advisor_agents')
    op.drop_index('ix_advisor_agents_id', 'advisor_agents')
    op.drop_table('advisor_agents')

    # Drop enums
    sa.Enum(name='memorytype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='agentstatus').drop(op.get_bind(), checkfirst=True)
