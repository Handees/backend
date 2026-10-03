"""empty message

Revision ID: 2f571f4cdb07
Revises: 5a01c2761e15
Create Date: 2026-10-03 16:09:23.685593

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2f571f4cdb07'
down_revision = '5a01c2761e15'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('request_location', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.drop_column('request_location')
