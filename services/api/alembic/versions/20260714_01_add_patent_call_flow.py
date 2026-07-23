"""add patent-aligned call flow tables

Revision ID: 20260714_01
Revises:
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa

from app.models import GUID


revision = "20260714_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_table(
        "call_sessions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("senior_id", GUID(), nullable=False),
        sa.Column("call_event_id", GUID(), nullable=True),
        sa.Column("caller_number_hash", sa.Text(), nullable=False),
        sa.Column("caller_number_last4", sa.String(length=4), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("family_number_matched", sa.Boolean(), nullable=False),
        sa.Column("matched_family_member_id", GUID(), nullable=True),
        sa.Column("suspected", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["call_event_id"], ["call_events.id"]),
        sa.ForeignKeyConstraint(["matched_family_member_id"], ["family_members.id"]),
        sa.ForeignKeyConstraint(["senior_id"], ["seniors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_sessions_caller_number_hash", "call_sessions", ["caller_number_hash"])

    op.create_table(
        "family_confirmations",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("call_session_id", GUID(), nullable=False),
        sa.Column("family_member_id", GUID(), nullable=True),
        sa.Column("guardian_id", GUID(), nullable=True),
        sa.Column("notification_id", GUID(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("response", sa.String(length=30), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_member_id"], ["family_members.id"]),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"]),
        sa.ForeignKeyConstraint(["notification_id"], ["emergency_notifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_confirmations_call_session_id", "family_confirmations", ["call_session_id"])

    op.create_table(
        "device_push_tokens",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("guardian_id", GUID(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_device_push_tokens_guardian_id", "device_push_tokens", ["guardian_id"])
    op.create_table(
        "push_deliveries",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("confirmation_id", GUID(), nullable=False),
        sa.Column("push_token_id", GUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["confirmation_id"], ["family_confirmations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["push_token_id"], ["device_push_tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_deliveries_confirmation_id", "push_deliveries", ["confirmation_id"])

    op.create_table(
        "risk_decisions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("call_session_id", GUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("number_mismatch", sa.Boolean(), nullable=False),
        sa.Column("speaker_similarity", sa.Float(), nullable=True),
        sa.Column("spoof_probability", sa.Float(), nullable=True),
        sa.Column("content_risk_score", sa.Integer(), nullable=True),
        sa.Column("family_response", sa.String(length=30), nullable=True),
        sa.Column("face_match_score", sa.Integer(), nullable=True),
        sa.Column("voice_profile_id", GUID(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("transcript_language", sa.String(length=20), nullable=True),
        sa.Column("transcript_confidence", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason_codes", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("model_versions_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("call_session_id", "sequence", name="uq_risk_decision_session_sequence"),
    )
    op.create_index("ix_risk_decisions_call_session_id", "risk_decisions", ["call_session_id"])

    op.create_table(
        "response_actions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("call_session_id", GUID(), nullable=False),
        sa.Column("risk_decision_id", GUID(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risk_decision_id"], ["risk_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_response_actions_call_session_id", "response_actions", ["call_session_id"])


def downgrade() -> None:
    op.drop_index("ix_response_actions_call_session_id", table_name="response_actions")
    op.drop_table("response_actions")
    op.drop_index("ix_risk_decisions_call_session_id", table_name="risk_decisions")
    op.drop_table("risk_decisions")
    op.drop_index("ix_push_deliveries_confirmation_id", table_name="push_deliveries")
    op.drop_table("push_deliveries")
    op.drop_index("ix_device_push_tokens_guardian_id", table_name="device_push_tokens")
    op.drop_table("device_push_tokens")
    op.drop_index("ix_family_confirmations_call_session_id", table_name="family_confirmations")
    op.drop_table("family_confirmations")
    op.drop_index("ix_call_sessions_caller_number_hash", table_name="call_sessions")
    op.drop_table("call_sessions")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
