"""add media import phone and consent verification

Revision ID: 20260719_09
Revises: 20260719_08
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_09"
down_revision = "20260719_08"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("media_import_sessions") as batch_op:
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("media_import_sessions") as batch_op:
        batch_op.drop_column("consented_at")
        batch_op.drop_column("phone_verified_at")
