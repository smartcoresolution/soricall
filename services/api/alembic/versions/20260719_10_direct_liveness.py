"""add direct enrollment liveness metadata

Revision ID: 20260719_10
Revises: 20260719_09
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_10"
down_revision = "20260719_09"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.add_column(sa.Column("liveness_action", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("liveness_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("liveness_verified_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("enrollment_invitations") as batch_op:
        batch_op.drop_column("liveness_verified_at")
        batch_op.drop_column("liveness_expires_at")
        batch_op.drop_column("liveness_action")
