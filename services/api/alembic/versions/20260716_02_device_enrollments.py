"""add protected device enrollments

Revision ID: 20260716_02
Revises: 20260716_01
"""

from alembic import op
import sqlalchemy as sa

from app.models import GUID

revision = "20260716_02"
down_revision = "20260716_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_enrollments",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("senior_id", GUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permissions_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["senior_id"], ["seniors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_device_enrollments_senior_id", "device_enrollments", ["senior_id"])
    op.create_index("ix_device_enrollments_token_hash", "device_enrollments", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("device_enrollments")
