"""replace email signup with verified phone signup

Revision ID: 20260716_01
Revises: 20260714_03
"""

from alembic import op
import sqlalchemy as sa

from app.models import GUID


revision = "20260716_01"
down_revision = "20260714_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical development data may contain the same family phone number on
    # multiple legacy email accounts. Preserve those rows; the new registration
    # endpoint rejects duplicate phone numbers before inserting new accounts.
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=False)
    op.create_table(
        "phone_verifications",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_phone_verifications_phone_number", "phone_verifications", ["phone_number"])


def downgrade() -> None:
    op.drop_table("phone_verifications")
    op.drop_index("ix_users_phone_number", table_name="users")
