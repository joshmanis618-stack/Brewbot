"""Add equipment craft/still_type, recipe spirits_style, and mash_steps table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('equipment', sa.Column('craft', sa.String(20), nullable=True, server_default='beer'))
    op.add_column('equipment', sa.Column('still_type', sa.String(50), nullable=True))

    op.add_column('recipes', sa.Column('spirits_style', sa.String(100), nullable=True))

    op.create_table(
        'mash_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('temp_c', sa.Float(), nullable=False),
        sa.Column('time_min', sa.Integer(), nullable=False),
        sa.Column('additions', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('mash_steps')
    op.drop_column('recipes', 'spirits_style')
    op.drop_column('equipment', 'still_type')
    op.drop_column('equipment', 'craft')
