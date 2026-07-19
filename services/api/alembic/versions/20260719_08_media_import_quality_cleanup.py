"""add media import quality and purge metadata

Revision ID: 20260719_08
Revises: 20260719_07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_08"
down_revision = "20260719_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media_import_sessions") as batch_op:
        batch_op.add_column(sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="PENDING"))
        batch_op.add_column(sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media_import_sessions") as batch_op:
        batch_op.drop_column("purged_at")
        batch_op.drop_column("quality_status")
