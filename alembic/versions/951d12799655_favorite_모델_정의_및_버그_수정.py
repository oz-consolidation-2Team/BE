"""favorite 모델 정의 및 버그 수정

Revision ID: 951d12799655
Revises: d959895ddab0
Create Date: 2025-04-09 08:14:38.752382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '951d12799655'
down_revision: Union[str, None] = 'd959895ddab0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('job_postings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=50), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=True),
    sa.Column('recruit_period_start', sa.Date(), nullable=True),
    sa.Column('recruit_period_end', sa.Date(), nullable=True),
    sa.Column('is_always_recruiting', sa.Boolean(), nullable=True),
    sa.Column('education', sa.Enum('none', 'high', 'college_2', 'college_4', 'graduate', name='education_enum'), nullable=False),
    sa.Column('recruit_number', sa.Integer(), nullable=False),
    sa.Column('benefits', sa.Text(), nullable=True),
    sa.Column('preferred_conditions', sa.Text(), nullable=True),
    sa.Column('other_conditions', sa.Text(), nullable=True),
    sa.Column('work_address', sa.String(length=255), nullable=False),
    sa.Column('work_place_name', sa.String(length=25), nullable=False),
    sa.Column('payment_method', sa.Enum('hourly', 'daily', 'weekly', 'monthly', 'yearly', name='payment_method_enum'), nullable=False),
    sa.Column('job_category', sa.Enum('food', 'sales', 'culture', 'service', 'admin', 'cs', 'labor', 'it', 'education', 'design', 'media', 'delivery', 'medical', 'pro_consult', 'pro_admin', 'pro_bar', 'pro_labor', 'pro_food', name='job_category_enum'), nullable=False),
    sa.Column('work_duration', sa.Enum('more_3_months', 'more_6_months', 'more_1_year', 'more_3_years', 'negotiable', name='work_duration_enum'), nullable=True),
    sa.Column('career', sa.String(length=50), nullable=False),
    sa.Column('employment_type', sa.String(length=50), nullable=False),
    sa.Column('salary', sa.Integer(), nullable=False),
    sa.Column('deadline_at', sa.Date(), nullable=False),
    sa.Column('work_days', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('posings_image', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['company_users.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company_info.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('favorite',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('job_posting_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['job_posting_id'], ['job_postings.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('favorite')
    op.drop_table('job_postings')
    # ### end Alembic commands ###
