"""Add interests and user_interests table, modify user

Revision ID: eb7721c5bb86
Revises: b896ec4e37e9
Create Date: 2025-04-11 05:19:27.588742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eb7721c5bb86'
down_revision: Union[str, None] = 'b896ec4e37e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('interests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('is_custom', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('user_interests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('interest_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['interest_id'], ['interests.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'interest_id', name='uq_user_interest')
    )
    op.drop_column('users', 'custom_interest')
    op.drop_column('users', 'interests')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('interests', postgresql.ENUM('office', 'service', 'tech', 'education', 'public', 'driver', 'etc', name='jobinterest_enum'), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('custom_interest', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_table('user_interests')
    op.drop_table('interests')
    # ### end Alembic commands ###
