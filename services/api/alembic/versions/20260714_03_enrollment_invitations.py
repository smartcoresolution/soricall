"""add family biometric enrollment invitations

Revision ID: 20260714_03
Revises: 20260714_02
"""

from alembic import op
import sqlalchemy as sa

from app.models import GUID


revision = "20260714_03"
down_revision = "20260714_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrollment_invitations",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("family_id", GUID(), nullable=False),
        sa.Column("family_member_id", GUID(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_member_id"], ["family_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_enrollment_invitations_family_id", "enrollment_invitations", ["family_id"])
    op.create_index("ix_enrollment_invitations_family_member_id", "enrollment_invitations", ["family_member_id"])
    op.create_index("ix_enrollment_invitations_token_hash", "enrollment_invitations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("enrollment_invitations")
