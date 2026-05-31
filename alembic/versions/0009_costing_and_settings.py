"""ingredient cost fields and app_settings table

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('fermentables', sa.Column('cost_per_kg', sa.Float(), nullable=True))
    op.add_column('hops', sa.Column('cost_per_kg', sa.Float(), nullable=True))
    op.add_column('yeasts', sa.Column('cost_per_pkg', sa.Float(), nullable=True))
    op.add_column('miscs', sa.Column('cost_per_unit', sa.Float(), nullable=True))

    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade():
    op.drop_table('app_settings')
    op.drop_column('miscs', 'cost_per_unit')
    op.drop_column('yeasts', 'cost_per_pkg')
    op.drop_column('hops', 'cost_per_kg')
    op.drop_column('fermentables', 'cost_per_kg')
