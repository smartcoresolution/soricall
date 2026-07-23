"""add invitation asset request and phone verification state

Revision ID: 20260719_03
Revises: 20260719_02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_03"
down_revision = "20260719_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.add_column(
            sa.Column("requested_assets", sa.String(length=100), nullable=False, server_default="VOICE,FACE")
        )
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("used_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.drop_column("used_at")
        batch_op.drop_column("phone_verified_at")
        batch_op.drop_column("requested_assets")
