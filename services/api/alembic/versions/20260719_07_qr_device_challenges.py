"""add device keys and signed QR challenges

Revision ID: 20260719_07
Revises: 20260719_06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_07"
down_revision = "20260719_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("algorithm", sa.String(length=30), nullable=False),
        sa.Column("public_key_der_b64", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_keys_user_id", "device_keys", ["user_id"])
    op.create_index("ix_device_keys_device_id", "device_keys", ["device_id"])
    op.create_index("ix_device_keys_fingerprint", "device_keys", ["fingerprint"], unique=True)
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.add_column(sa.Column("device_key_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("device_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_enrollment_invitation_device_key", "device_keys", ["device_key_id"], ["id"])
    op.create_table(
        "enrollment_qr_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invitation_id", sa.Uuid(), nullable=False),
        sa.Column("device_key_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invitation_id"], ["enrollment_invitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_key_id"], ["device_keys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrollment_qr_challenges_invitation_id", "enrollment_qr_challenges", ["invitation_id"])
    op.create_index("ix_enrollment_qr_challenges_device_key_id", "enrollment_qr_challenges", ["device_key_id"])


def downgrade() -> None:
    op.drop_table("enrollment_qr_challenges")
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.drop_constraint("fk_enrollment_invitation_device_key", type_="foreignkey")
        batch_op.drop_column("device_verified_at")
        batch_op.drop_column("device_key_id")
    op.drop_table("device_keys")
