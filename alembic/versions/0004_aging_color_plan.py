"""Add color_srm to barrel_aging_entries and target_55gal_months to barrel_aging_records

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('barrel_aging_entries',
                  sa.Column('color_srm', sa.Float(), nullable=True))
    op.add_column('barrel_aging_records',
                  sa.Column('target_55gal_months', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('barrel_aging_records', 'target_55gal_months')
    op.drop_column('barrel_aging_entries', 'color_srm')
