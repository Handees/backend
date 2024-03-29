"""empty message

Revision ID: 640f264b8ea8
Revises: 280ac11a57ca
Create Date: 2022-09-05 09:51:30.554970

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '640f264b8ea8'
down_revision = '280ac11a57ca'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'payment', 'method',
        existing_type=sa.Enum('CASH', 'CARD', name='paymentmethodenum'),
        nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'payment', 'method',
        existing_type=sa.VARCHAR(length=50),
        nullable=True
    )
    # ### end Alembic commands ###
