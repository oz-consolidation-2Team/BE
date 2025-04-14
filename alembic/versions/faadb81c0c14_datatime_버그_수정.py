"""datatime 버그 수정

Revision ID: faadb81c0c14
Revises: 951d12799655
Create Date: 2025-04-09 08:19:14.800376

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "faadb81c0c14"
down_revision: Union[str, None] = "951d12799655"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "job_postings",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "job_postings",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###
