"""Private Rooms

Revision ID: b72615ab0cb4
Revises: 0c2ac5c05c3b
Create Date: 2025-01-21 16:49:53.227768

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b72615ab0cb4'
down_revision: Union[str, None] = '0c2ac5c05c3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('private_room_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('action_type', sa.Enum('invite', 'kick', 'change', name='privateactiontypeenum'), nullable=False),
    sa.Column('object', sa.BigInteger(), nullable=False),
    sa.Column('before', sa.String(), nullable=True),
    sa.Column('after', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('private_room',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('timestamp_create', sa.BigInteger(), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=False),
    sa.Column('role_id', sa.BigInteger(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('color', sa.String(), nullable=False),
    sa.Column('icon', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.alter_column('time_counter_log', 'timestamp',
               existing_type=sa.BIGINT(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('time_counter_log', 'timestamp',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.drop_table('private_room')
    op.drop_table('private_room_log')
    # ### end Alembic commands ###
