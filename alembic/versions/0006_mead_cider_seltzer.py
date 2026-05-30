"""Add mead, cider, and seltzer style columns to recipes

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('recipes', sa.Column('mead_style',    sa.String(100), nullable=True))
    op.add_column('recipes', sa.Column('cider_style',   sa.String(100), nullable=True))
    op.add_column('recipes', sa.Column('seltzer_style', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('recipes', 'seltzer_style')
    op.drop_column('recipes', 'cider_style')
    op.drop_column('recipes', 'mead_style')
