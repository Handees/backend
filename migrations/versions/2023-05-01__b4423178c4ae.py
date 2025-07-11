"""empty message

Revision ID: b4423178c4ae
Revises: f14fa6341a65
Create Date: 2023-05-01 22:44:46.689801

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b4423178c4ae'
down_revision = 'f14fa6341a65'
branch_labels = None
depends_on = None


def upgrade():
    # create the enum type
    paymentstatusenum = postgresql.ENUM(
        'PENDING',
        'FAILED',
        'SUCCESS',
        'TIMEOUT',
        name='paymentstatusenum',
        create_type=True
    )
    paymentstatusenum.create(op.get_bind())
    op.drop_column('payment', 'status')
    op.add_column(
        'payment',  # table name
        sa.Column(
            'status',
            postgresql.ENUM(
                'PENDING',
                'FAILED',
                'SUCCESS',
                'TIMEOUT',
                name='paymentstatusenum',
                create_type=True
            ),
            nullable=True
        )
    )


def downgrade():
    # drop the enum type and revert the column to its previous data type
    op.alter_column(
        'payment',  # table name
        'status',  # column name
        existing_type=postgresql.ENUM(
            'PENDING',
            'FAILED',
            'SUCCESS',
            'TIMEOUT',
            name='paymentstatusenum',
            create_type=True
        ),  # existing data type
        type_=sa.Boolean(),  # previous data type
    )
    postgresql.ENUM(name='paymentstatusenum').drop(op.get_bind())
