"""link confirmation contacts to protected call users

Revision ID: 20260719_01
Revises: 20260716_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_01"
down_revision = "20260716_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.add_column(sa.Column("protected_user_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_family_members_protected_user_id_seniors",
            "seniors",
            ["protected_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_family_members_protected_user_id",
            ["protected_user_id"],
            unique=False,
        )

    # Legacy confirmation contacts can be assigned safely when their family has
    # exactly one protected call user. Ambiguous rows remain NULL for explicit
    # operational review instead of being linked to the wrong person.
    op.execute(
        """
        UPDATE family_members
        SET protected_user_id = (
            SELECT seniors.id
            FROM seniors
            WHERE seniors.family_id = family_members.family_id
            LIMIT 1
        )
        WHERE member_type = 'FAMILY_CONFIRMATION_CONTACT'
          AND protected_user_id IS NULL
          AND (
              SELECT COUNT(*)
              FROM seniors
              WHERE seniors.family_id = family_members.family_id
          ) = 1
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.drop_index("ix_family_members_protected_user_id")
        batch_op.drop_column("protected_user_id")
