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
    name='kycstatusenum',
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


def downgrade():
    op.drop_column('artisan', 'kyc_status')
    bind = op.get_bind()
    kycstatusenum.drop(bind, checkfirst=False)
