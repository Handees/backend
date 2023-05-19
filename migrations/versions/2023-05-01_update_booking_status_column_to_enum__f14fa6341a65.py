"""update booking status column to enum type

Revision ID: f14fa6341a65
Revises: 79904e56d60b
Create Date: 2023-05-01 14:43:06.584765

"""
from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision = 'f14fa6341a65'
down_revision = '79904e56d60b'
branch_labels = None
depends_on = None


def upgrade():
    # create the enum type
    bookingstatusenum = postgresql.ENUM(
        'IN_PROGRESS',
        'COMPLETED',
        'CANCELLED',
        'ARTISAN_ARRIVED',
        name='bookingstatusenum',
        create_type=True
    )
    bookingstatusenum.create(op.get_bind())
    op.drop_column('booking', 'status')
    op.add_column(
        'booking',  # table name
        sa.Column(
            'status',
            postgresql.ENUM(
                'IN_PROGRESS',
                'COMPLETED',
                'CANCELLED',
                'ARTISAN_ARRIVED',
                name='bookingstatusenum'
            ),
            nullable=True
        )
    )


def downgrade():
    # drop the enum type and revert the column to its previous data type
    op.alter_column(
        'booking',  # table name
        'status',  # column name
        existing_type=postgresql.ENUM(
            'IN_PROGRESS',
            'COMPLETED',
            'CANCELLED',
            'ARTISAN_ARRIVED',
            name='bookingstatusenum'
        ),  # existing data type
        type_=sa.Integer(),  # previous data type
        existing_nullable=False,  # existing nullability
        server_default='0',  # default value if the column is null
        postgresql_using='status::integer'  # using clause
    )
    postgresql.ENUM(name='bookingstatusenum').drop(op.get_bind())
