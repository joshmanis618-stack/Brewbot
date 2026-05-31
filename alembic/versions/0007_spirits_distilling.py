"""Add still run log, spirit cuts, and barrel disposition entries

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend barrel_aging_records with spirits fields
    op.add_column('barrel_aging_records', sa.Column('fill_proof', sa.Float(), nullable=True))
    op.add_column('barrel_aging_records', sa.Column('disposition', sa.String(30), nullable=True, server_default='aging'))

    # Still run log
    op.create_table('still_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('run_number', sa.Integer(), nullable=True),
        sa.Column('run_date', sa.DateTime(), nullable=True),
        sa.Column('charge_volume_l', sa.Float(), nullable=True),
        sa.Column('charge_abv', sa.Float(), nullable=True),
        sa.Column('still_type', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['brew_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Per-cut data with sensory log
    op.create_table('still_cuts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('still_run_id', sa.Integer(), nullable=False),
        sa.Column('cut_type', sa.String(20), nullable=False),
        sa.Column('volume_l', sa.Float(), nullable=True),
        sa.Column('start_abv', sa.Float(), nullable=True),
        sa.Column('end_abv', sa.Float(), nullable=True),
        sa.Column('appearance', sa.String(200), nullable=True),
        sa.Column('aroma', sa.Text(), nullable=True),
        sa.Column('flavor', sa.Text(), nullable=True),
        sa.Column('finish', sa.Text(), nullable=True),
        sa.Column('overall_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['still_run_id'], ['still_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Barrel disposition / age statement log
    op.create_table('barrel_disposition_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('proof_at_action', sa.Float(), nullable=True),
        sa.Column('volume_l', sa.Float(), nullable=True),
        sa.Column('destination', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['record_id'], ['barrel_aging_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('barrel_disposition_entries')
    op.drop_table('still_cuts')
    op.drop_table('still_runs')
    op.drop_column('barrel_aging_records', 'disposition')
    op.drop_column('barrel_aging_records', 'fill_proof')
