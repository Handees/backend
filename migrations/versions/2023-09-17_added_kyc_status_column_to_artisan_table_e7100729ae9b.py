"""added kyc status column to artisan table

Revision ID: e7100729ae9b
Revises: d5f3bcdc9442
Create Date: 2023-09-17 03:59:50.590270

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e7100729ae9b'
down_revision = 'd5f3bcdc9442'
branch_labels = None
depends_on = None


kycstatusenum = postgresql.ENUM(
    'UNINITIALIZED',
    'IN_PROGRESS',
    'COMPLETED',
    name='kyc_status_enum',
    create_type=True
)


def upgrade():
    # create the enum type
    kycstatusenum.create(op.get_bind())
    # set column
    op.add_column(
        'artisan',  # table name
        sa.Column(
            'kyc_status',
            kycstatusenum,
            nullable=False,
            default='UNINITIALIZED'
        )
    )

    with op.batch_alter_table('payment', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('transaction_reference', sa.String(), nullable=True)
        )
        batch_op.create_unique_constraint(
            'payment_transaction_reference_key', ['transaction_reference']
        )


def downgrade():
    op.drop_column('artisan', 'kyc_status')
    bind = op.get_bind()
    kycstatusenum.drop(bind, checkfirst=False)

    with op.batch_alter_table('payment', schema=None) as batch_op:
        batch_op.drop_constraint('payment_transaction_reference_key', type_='unique')
        batch_op.drop_column('transaction_reference')
