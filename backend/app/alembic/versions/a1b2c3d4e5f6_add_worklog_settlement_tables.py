"""Add worklog settlement tables

Revision ID: a1b2c3d4e5f6
Revises: 1a31ce608336
Create Date: 2026-03-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Add hourly_rate to user table
    op.add_column('user', sa.Column('hourly_rate', sa.Float(), nullable=True, server_default='25.0'))

    # Create worklog table
    op.create_table(
        'worklog',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_worklog_user_id'), 'worklog', ['user_id'], unique=False)

    # Create time_segment table
    op.create_table(
        'time_segment',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('worklog_id', sa.Uuid(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['worklog_id'], ['worklog.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_time_segment_worklog_id'), 'time_segment', ['worklog_id'], unique=False)

    # Create adjustment table (adjustmenttype enum auto-created by sa.Enum)
    op.create_table(
        'adjustment',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('worklog_id', sa.Uuid(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=True),
        sa.Column('adjustment_type', sa.Enum('DEDUCTION', 'BONUS', name='adjustmenttype'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['worklog_id'], ['worklog.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_adjustment_worklog_id'), 'adjustment', ['worklog_id'], unique=False)

    # Create remittance table (remittancestatus enum auto-created by sa.Enum)
    op.create_table(
        'remittance',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED', name='remittancestatus'), nullable=False),
        sa.Column('period_label', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_remittance_user_id'), 'remittance', ['user_id'], unique=False)

    # Create remittance_line_item table
    op.create_table(
        'remittance_line_item',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('remittance_id', sa.Uuid(), nullable=False),
        sa.Column('worklog_id', sa.Uuid(), nullable=False),
        sa.Column('amount_settled', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['remittance_id'], ['remittance.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worklog_id'], ['worklog.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_remittance_line_item_remittance_id'), 'remittance_line_item', ['remittance_id'], unique=False)
    op.create_index(op.f('ix_remittance_line_item_worklog_id'), 'remittance_line_item', ['worklog_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_remittance_line_item_worklog_id'), table_name='remittance_line_item')
    op.drop_index(op.f('ix_remittance_line_item_remittance_id'), table_name='remittance_line_item')
    op.drop_table('remittance_line_item')

    op.drop_index(op.f('ix_remittance_user_id'), table_name='remittance')
    op.drop_table('remittance')

    op.drop_index(op.f('ix_adjustment_worklog_id'), table_name='adjustment')
    op.drop_table('adjustment')

    op.drop_index(op.f('ix_time_segment_worklog_id'), table_name='time_segment')
    op.drop_table('time_segment')

    op.drop_index(op.f('ix_worklog_user_id'), table_name='worklog')
    op.drop_table('worklog')

    op.drop_column('user', 'hourly_rate')

    sa.Enum('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED', name='remittancestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum('DEDUCTION', 'BONUS', name='adjustmenttype').drop(op.get_bind(), checkfirst=True)
