"""add explicit call-protection family roles

Revision ID: 20260714_02
Revises: 20260714_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_02"
down_revision = "20260714_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seniors", sa.Column("member_type", sa.String(40), nullable=False, server_default="PROTECTED_CALL_USER"))
    op.add_column("seniors", sa.Column("relation_code", sa.String(40), nullable=False, server_default="OTHER"))
    op.add_column("seniors", sa.Column("protection_status", sa.String(30), nullable=False, server_default="PREPARING"))
    op.add_column("family_members", sa.Column("member_type", sa.String(40), nullable=False, server_default="FAMILY_CONFIRMATION_CONTACT"))
    op.add_column("family_members", sa.Column("relation_code", sa.String(40), nullable=True))
    op.add_column("family_members", sa.Column("is_primary_contact", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("family_members", sa.Column("notification_priority", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("family_members", sa.Column("notify_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("family_members", "notify_enabled")
    op.drop_column("family_members", "notification_priority")
    op.drop_column("family_members", "is_primary_contact")
    op.drop_column("family_members", "relation_code")
    op.drop_column("family_members", "member_type")
    op.drop_column("seniors", "protection_status")
    op.drop_column("seniors", "relation_code")
    op.drop_column("seniors", "member_type")
