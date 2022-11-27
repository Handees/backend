"""empty message

Revision ID: 436703003dcb
Revises: 0638db434454
Create Date: 2022-10-04 16:46:26.940759

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '436703003dcb'
down_revision = '0638db434454'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('booking_contract', 'start_time',
               existing_type=sa.DATE(),
               nullable=False)
    op.drop_column('booking_contract', 'agreed_end_time')
    op.drop_column('booking_contract', 'agreed_start_time')
    op.add_column('payment', sa.Column('regulatory_charge', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('payment', 'regulatory_charge')
    op.add_column('booking_contract', sa.Column('agreed_start_time', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('booking_contract', sa.Column('agreed_end_time', sa.DATE(), autoincrement=False, nullable=True))
    op.alter_column('booking_contract', 'start_time',
               existing_type=sa.DATE(),
               nullable=True)
    # ### end Alembic commands ###
