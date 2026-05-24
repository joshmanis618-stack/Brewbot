"""Add barrel_style, wood_contact_area_cm2, and storage_temp_c to barrels

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('barrels', sa.Column('barrel_style', sa.String(20), nullable=True, server_default='traditional'))
    op.add_column('barrels', sa.Column('wood_contact_area_cm2', sa.Float(), nullable=True))
    op.add_column('barrels', sa.Column('storage_temp_c', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('barrels', 'storage_temp_c')
    op.drop_column('barrels', 'wood_contact_area_cm2')
    op.drop_column('barrels', 'barrel_style')
