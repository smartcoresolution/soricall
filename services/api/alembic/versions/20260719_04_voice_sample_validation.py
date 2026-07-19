"""add voice sample validation and deletion metadata

Revision ID: 20260719_04
Revises: 20260719_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_04"
down_revision = "20260719_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("voice_samples") as batch_op:
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("size_bytes", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("validation_status", sa.String(length=30), nullable=False, server_default="LEGACY")
        )
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_voice_samples_content_hash", ["content_hash"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("voice_samples") as batch_op:
        batch_op.drop_index("ix_voice_samples_content_hash")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("validation_status")
        batch_op.drop_column("size_bytes")
        batch_op.drop_column("content_hash")
