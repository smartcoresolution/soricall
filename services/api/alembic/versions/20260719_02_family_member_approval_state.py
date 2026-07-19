"""add family member approval state and trust level

Revision ID: 20260719_02
Revises: 20260719_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_02"
down_revision = "20260719_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.add_column(sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="DRAFT"))
        batch_op.add_column(sa.Column("trust_level", sa.String(length=1), nullable=False, server_default="D"))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("approved_by", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("revocation_reason", sa.String(length=255), nullable=True))
        batch_op.create_foreign_key(
            "fk_family_members_approved_by_users",
            "users",
            ["approved_by"],
            ["id"],
        )

    op.execute(
        """
        UPDATE family_members
        SET approval_status = CASE WHEN is_verified THEN 'ACTIVE' ELSE 'DRAFT' END,
            trust_level = CASE WHEN is_verified THEN 'B' ELSE 'D' END
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.drop_column("revocation_reason")
        batch_op.drop_column("revoked_at")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("trust_level")
        batch_op.drop_column("approval_status")
