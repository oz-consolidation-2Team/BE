"""change

Revision ID: 33091bd8b192
Revises: fd92936457fc
Create Date: 2025-04-14 02:37:16.581451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33091bd8b192'
down_revision: Union[str, None] = 'fd92936457fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('resumes_user_id_fkey', 'resumes', type_='foreignkey')
    op.create_foreign_key(None, 'resumes', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('resumes_educations_resumes_id_fkey', 'resumes_educations', type_='foreignkey')
    op.create_foreign_key(None, 'resumes_educations', 'resumes', ['resumes_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'resumes_educations', type_='foreignkey')
    op.create_foreign_key('resumes_educations_resumes_id_fkey', 'resumes_educations', 'resumes', ['resumes_id'], ['id'])
    op.drop_constraint(None, 'resumes', type_='foreignkey')
    op.create_foreign_key('resumes_user_id_fkey', 'resumes', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###
