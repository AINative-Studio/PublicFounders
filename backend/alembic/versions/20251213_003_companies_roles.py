"""Add companies and company_roles tables

Revision ID: 003_companies_roles
Revises: 002_goals_asks_posts
Create Date: 2025-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_companies_roles'
down_revision: Union[str, None] = '002_goals_asks_posts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create companies and company_roles tables"""

    # Create CompanyStage enum
    company_stage_enum = postgresql.ENUM('idea', 'pre-seed', 'seed', 'series-a', 'series-b+', name='companystage')
    company_stage_enum.create(op.get_bind(), checkfirst=True)

    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stage', sa.Enum('idea', 'pre-seed', 'seed', 'series-a', 'series-b+', name='companystage'), nullable=False),
        sa.Column('industry', sa.String(255), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('embedding_updated_at', sa.DateTime(), nullable=True)
    )

    # Create indexes for companies table
    op.create_index('ix_companies_id', 'companies', ['id'])
    op.create_index('ix_companies_name', 'companies', ['name'])
    op.create_index('ix_companies_stage', 'companies', ['stage'])
    op.create_index('ix_companies_industry', 'companies', ['industry'])
    op.create_index('ix_companies_embedding_id', 'companies', ['embedding_id'])

    # Create company_roles table
    op.create_table(
        'company_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(255), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE')
    )

    # Create indexes for company_roles table
    op.create_index('ix_company_roles_id', 'company_roles', ['id'])
    op.create_index('ix_company_roles_user_id', 'company_roles', ['user_id'])
    op.create_index('ix_company_roles_company_id', 'company_roles', ['company_id'])
    op.create_index('ix_company_roles_is_current', 'company_roles', ['is_current'])


def downgrade() -> None:
    """Drop tables and enums"""
    op.drop_index('ix_company_roles_is_current', 'company_roles')
    op.drop_index('ix_company_roles_company_id', 'company_roles')
    op.drop_index('ix_company_roles_user_id', 'company_roles')
    op.drop_index('ix_company_roles_id', 'company_roles')
    op.drop_table('company_roles')

    op.drop_index('ix_companies_embedding_id', 'companies')
    op.drop_index('ix_companies_industry', 'companies')
    op.drop_index('ix_companies_stage', 'companies')
    op.drop_index('ix_companies_name', 'companies')
    op.drop_index('ix_companies_id', 'companies')
    op.drop_table('companies')

    # Drop enum
    sa.Enum(name='companystage').drop(op.get_bind(), checkfirst=True)
