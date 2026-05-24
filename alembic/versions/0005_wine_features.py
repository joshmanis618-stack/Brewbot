"""Add wine harvest intake fields, MLF tracker, and fining agent log

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Wine harvest intake fields on brew_sessions
    op.add_column('brew_sessions', sa.Column('brix_intake', sa.Float(), nullable=True))
    op.add_column('brew_sessions', sa.Column('ph_intake', sa.Float(), nullable=True))
    op.add_column('brew_sessions', sa.Column('ta_intake_g_l', sa.Float(), nullable=True))
    op.add_column('brew_sessions', sa.Column('fruit_weight_kg', sa.Float(), nullable=True))
    op.add_column('brew_sessions', sa.Column('crush_date', sa.DateTime(), nullable=True))
    op.add_column('brew_sessions', sa.Column('fruit_source', sa.String(300), nullable=True))

    # MLF tracking entries
    op.create_table(
        'wine_mlf_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('brew_sessions.id'), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('strain', sa.String(100), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('result', sa.String(20), nullable=True),
        sa.Column('notes', sa.String(300), nullable=True),
    )

    # Fining agent log entries
    op.create_table(
        'wine_fining_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('brew_sessions.id'), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('agent', sa.String(100), nullable=False),
        sa.Column('rate_g_per_hl', sa.Float(), nullable=True),
        sa.Column('volume_l', sa.Float(), nullable=True),
        sa.Column('purpose', sa.String(200), nullable=True),
        sa.Column('notes', sa.String(300), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('wine_fining_entries')
    op.drop_table('wine_mlf_entries')
    op.drop_column('brew_sessions', 'fruit_source')
    op.drop_column('brew_sessions', 'crush_date')
    op.drop_column('brew_sessions', 'fruit_weight_kg')
    op.drop_column('brew_sessions', 'ta_intake_g_l')
    op.drop_column('brew_sessions', 'ph_intake')
    op.drop_column('brew_sessions', 'brix_intake')
