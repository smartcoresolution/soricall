"""expand phone verification purpose for device enrollment UUIDs

Revision ID: 20260716_03
Revises: 20260716_02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_03"
down_revision = "20260716_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "phone_verifications",
        "purpose",
        existing_type=sa.String(length=30),
        type_=sa.String(length=80),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "phone_verifications",
        "purpose",
        existing_type=sa.String(length=80),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
