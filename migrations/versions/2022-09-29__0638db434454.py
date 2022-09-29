"""empty message

Revision ID: 0638db434454
Revises: 4540c18e59f9
Create Date: 2022-09-29 03:30:36.222109

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0638db434454'
down_revision = '4540c18e59f9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('payment', sa.Column('transaction_id', sa.BigInteger(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('payment', 'transaction_id')
    # ### end Alembic commands ###
