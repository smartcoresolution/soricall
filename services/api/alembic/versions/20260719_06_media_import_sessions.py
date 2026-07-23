"""add external media import sessions

Revision ID: 20260719_06
Revises: 20260719_05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_06"
down_revision = "20260719_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_import_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("family_member_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("declared_mime_type", sa.String(length=100), nullable=False),
        sa.Column("detected_mime_type", sa.String(length=100), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("trust_level", sa.String(length=1), nullable=False),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_member_id"], ["family_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_import_sessions_family_id", "media_import_sessions", ["family_id"])
    op.create_index("ix_media_import_sessions_family_member_id", "media_import_sessions", ["family_member_id"])
    op.create_index("ix_media_import_sessions_content_hash", "media_import_sessions", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_media_import_sessions_content_hash", table_name="media_import_sessions")
    op.drop_index("ix_media_import_sessions_family_member_id", table_name="media_import_sessions")
    op.drop_index("ix_media_import_sessions_family_id", table_name="media_import_sessions")
    op.drop_table("media_import_sessions")
