"""session dry hops and packaging entries

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'session_dry_hops',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('hop_id', sa.Integer(), nullable=True),
        sa.Column('variety', sa.String(100), nullable=True),
        sa.Column('addition_date', sa.Date(), nullable=True),
        sa.Column('removal_date', sa.Date(), nullable=True),
        sa.Column('rate_g_per_l', sa.Float(), nullable=True),
        sa.Column('total_grams', sa.Float(), nullable=True),
        sa.Column('temp_c', sa.Float(), nullable=True),
        sa.Column('vessel', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['brew_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hop_id'], ['hops.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'packaging_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('package_date', sa.Date(), nullable=True),
        sa.Column('method', sa.String(20), nullable=True),
        sa.Column('vessel_count', sa.Integer(), nullable=True),
        sa.Column('fill_volume_l', sa.Float(), nullable=True),
        sa.Column('carbonation_vol', sa.Float(), nullable=True),
        sa.Column('priming_sugar_type', sa.String(50), nullable=True),
        sa.Column('priming_sugar_g', sa.Float(), nullable=True),
        sa.Column('co2_psi', sa.Float(), nullable=True),
        sa.Column('final_gravity', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['brew_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('packaging_entries')
    op.drop_table('session_dry_hops')
