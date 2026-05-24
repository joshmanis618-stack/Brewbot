"""Add craft, wine fields, barrel aging, and grape varieties

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Existing table additions ───────────────────────────────────────────────

    op.add_column('recipes', sa.Column('craft', sa.String(20), nullable=True, server_default='beer'))
    op.add_column('recipes', sa.Column('wine_style', sa.String(20), nullable=True))
    op.add_column('recipes', sa.Column('skin_contact_days', sa.Integer(), nullable=True))
    op.add_column('recipes', sa.Column('target_ta', sa.Float(), nullable=True))
    op.add_column('recipes', sa.Column('target_ph', sa.Float(), nullable=True))

    op.add_column('brew_sessions', sa.Column('craft', sa.String(20), nullable=True, server_default='beer'))

    op.add_column('fermentation_readings', sa.Column('ph', sa.Float(), nullable=True))
    op.add_column('fermentation_readings', sa.Column('ta', sa.Float(), nullable=True))
    op.add_column('fermentation_readings', sa.Column('so2_free', sa.Float(), nullable=True))
    op.add_column('fermentation_readings', sa.Column('so2_total', sa.Float(), nullable=True))

    # ── New tables ────────────────────────────────────────────────────────────

    op.create_table(
        'barrels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('size_l', sa.Float(), nullable=False),
        sa.Column('wood_type', sa.String(50), nullable=True),
        sa.Column('char_level', sa.String(50), nullable=True),
        sa.Column('previous_contents', sa.String(100), nullable=True),
        sa.Column('age_months', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'barrel_aging_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('barrel_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('target_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['barrel_id'], ['barrels.id']),
        sa.ForeignKeyConstraint(['session_id'], ['brew_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'barrel_aging_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('gravity', sa.Float(), nullable=True),
        sa.Column('abv', sa.Float(), nullable=True),
        sa.Column('flavor_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['record_id'], ['barrel_aging_records.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'grape_varieties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('origin', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'recipe_grapes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('grape_id', sa.Integer(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=True),
        sa.Column('amount_kg', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['grape_id'], ['grape_varieties.id']),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('recipe_grapes')
    op.drop_table('grape_varieties')
    op.drop_table('barrel_aging_entries')
    op.drop_table('barrel_aging_records')
    op.drop_table('barrels')
    op.drop_column('fermentation_readings', 'so2_total')
    op.drop_column('fermentation_readings', 'so2_free')
    op.drop_column('fermentation_readings', 'ta')
    op.drop_column('fermentation_readings', 'ph')
    op.drop_column('brew_sessions', 'craft')
    op.drop_column('recipes', 'target_ph')
    op.drop_column('recipes', 'target_ta')
    op.drop_column('recipes', 'skin_contact_days')
    op.drop_column('recipes', 'wine_style')
    op.drop_column('recipes', 'craft')
