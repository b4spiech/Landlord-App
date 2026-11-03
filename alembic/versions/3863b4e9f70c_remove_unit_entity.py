"""Remove unit entity

Revision ID: 3863b4e9f70c
Revises: 094fa2636bc5
Create Date: 2026-06-19 12:30:44.282053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3863b4e9f70c'
down_revision: Union[str, None] = '094fa2636bc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the FK columns that reference `unit` BEFORE dropping the table.
    with op.batch_alter_table('lease', schema=None) as batch_op:
        batch_op.drop_index('ix_lease_unit_id')
        batch_op.drop_constraint('lease_unit_id_fkey', type_='foreignkey')
        batch_op.drop_column('unit_id')

    with op.batch_alter_table('expense', schema=None) as batch_op:
        batch_op.drop_index('ix_expense_unit_id')
        batch_op.drop_constraint('expense_unit_id_fkey', type_='foreignkey')
        batch_op.drop_column('unit_id')

    with op.batch_alter_table('unit', schema=None) as batch_op:
        batch_op.drop_index('ix_unit_id')
        batch_op.drop_index('ix_unit_property_id')

    op.drop_table('unit')


def downgrade() -> None:
    # Recreate the `unit` table BEFORE re-adding the FK columns that reference it.
    op.create_table('unit',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('property_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('unit_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('bedrooms', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('bathrooms', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('square_feet', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('market_rent', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('notes', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['property_id'], ['property.id'], name='unit_property_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='unit_pkey')
    )
    with op.batch_alter_table('unit', schema=None) as batch_op:
        batch_op.create_index('ix_unit_property_id', ['property_id'], unique=False)
        batch_op.create_index('ix_unit_id', ['id'], unique=False)

    with op.batch_alter_table('lease', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_id', sa.UUID(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('lease_unit_id_fkey', 'unit', ['unit_id'], ['id'])
        batch_op.create_index('ix_lease_unit_id', ['unit_id'], unique=False)

    with op.batch_alter_table('expense', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_id', sa.UUID(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('expense_unit_id_fkey', 'unit', ['unit_id'], ['id'])
        batch_op.create_index('ix_expense_unit_id', ['unit_id'], unique=False)
