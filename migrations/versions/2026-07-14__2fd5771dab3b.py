"""empty message

Revision ID: 2fd5771dab3b
Revises: 37d06ec258e7
Create Date: 2026-07-14 02:04:18.243267

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2fd5771dab3b"
down_revision = "37d06ec258e7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP INDEX blob@blob_img_id_key CASCADE")
    op.execute("DROP INDEX blob@uix_img_id CASCADE")
    op.execute("DROP INDEX blob@uix_user_blob_type_filename CASCADE")
    with op.batch_alter_table("blob", schema=None) as batch_op:
        batch_op.drop_column("img_id")
    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table("blob", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("img_id", sa.VARCHAR(), autoincrement=False, nullable=False)
        )
    op.execute(
        "ALTER TABLE blob ADD CONSTRAINT uix_user_blob_type_filename UNIQUE (user_id, blob_type, filename)"
    )
    op.execute(
        "ALTER TABLE blob ADD CONSTRAINT uix_img_id UNIQUE (img_id)"
    )
    op.execute(
        "ALTER TABLE blob ADD CONSTRAINT blob_img_id_key UNIQUE (img_id)"
    )