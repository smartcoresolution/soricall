import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CHAR,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PhoneVerification(Base):
    __tablename__ = "phone_verifications"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    phone_number: Mapped[str] = mapped_column(String(50), index=True)
    code_hash: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(String(80), default="SIGNUP")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeviceEnrollment(Base):
    __tablename__ = "device_enrollments"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="INVITED")
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    permissions_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Family(Base):
    __tablename__ = "families"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["FamilyMember"]] = relationship(cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"))
    protected_user_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("seniors.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    relation: Mapped[str | None] = mapped_column(String(50))
    member_type: Mapped[str] = mapped_column(String(40), default="FAMILY_CONFIRMATION_CONTACT")
    relation_code: Mapped[str | None] = mapped_column(String(40))
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_priority: Mapped[int] = mapped_column(Integer, default=1)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    phone_number: Mapped[str | None] = mapped_column(String(50))
    phone_number_hash: Mapped[str | None] = mapped_column(Text)
    phone_number_last4: Mapped[str | None] = mapped_column(String(4))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    trust_level: Mapped[str] = mapped_column(String(1), default="D")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnrollmentInvitation(Base):
    __tablename__ = "enrollment_invitations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    family_member_id: Mapped[str] = mapped_column(GUID(), ForeignKey("family_members.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="SMS")
    requested_assets: Mapped[str] = mapped_column(String(100), default="VOICE,FACE")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    token_hash: Mapped[str] = mapped_column(Text, unique=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_key_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("device_keys.id"))
    device_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liveness_action: Mapped[str | None] = mapped_column(String(30))
    liveness_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liveness_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeviceKey(Base):
    __tablename__ = "device_keys"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(String(100), index=True)
    algorithm: Mapped[str] = mapped_column(String(30), default="ECDSA_P256_SHA256")
    public_key_der_b64: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnrollmentQrChallenge(Base):
    __tablename__ = "enrollment_qr_challenges"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    invitation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("enrollment_invitations.id", ondelete="CASCADE"), index=True
    )
    device_key_id: Mapped[str] = mapped_column(GUID(), ForeignKey("device_keys.id"), index=True)
    challenge_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MediaImportSession(Base):
    __tablename__ = "media_import_sessions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    family_member_id: Mapped[str] = mapped_column(GUID(), ForeignKey("family_members.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(30), default="EXTERNAL_SHARE")
    filename: Mapped[str] = mapped_column(String(255))
    declared_mime_type: Mapped[str] = mapped_column(String(100))
    detected_mime_type: Mapped[str | None] = mapped_column(String(100))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_UPLOAD")
    trust_level: Mapped[str] = mapped_column(String(1), default="D")
    failure_code: Mapped[str | None] = mapped_column(String(50))
    quality_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Senior(Base):
    __tablename__ = "seniors"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"))
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    member_type: Mapped[str] = mapped_column(String(40), default="PROTECTED_CALL_USER")
    relation_code: Mapped[str] = mapped_column(String(40), default="OTHER")
    protection_status: Mapped[str] = mapped_column(String(30), default="PREPARING")
    phone_number: Mapped[str | None] = mapped_column(String(50))
    phone_number_hash: Mapped[str | None] = mapped_column(Text)
    phone_number_last4: Mapped[str | None] = mapped_column(String(4))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"))
    relation: Mapped[str | None] = mapped_column(String(50))
    priority: Mapped[int] = mapped_column(Integer, default=1)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SafeWord(Base):
    __tablename__ = "safe_words"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"))
    word_hash: Mapped[str] = mapped_column(Text)
    hint: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_member_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("family_members.id", ondelete="CASCADE"),
    )
    display_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    consent_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("consent_logs.id"))
    embedding: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_version: Mapped[str | None] = mapped_column(String(50))
    quality_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VoiceSample(Base):
    __tablename__ = "voice_samples"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    voice_profile_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("voice_profiles.id", ondelete="CASCADE"),
    )
    object_key: Mapped[str | None] = mapped_column(Text)
    audio_ref: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(String(30))
    retained: Mapped[bool] = mapped_column(Boolean, default=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(30), default="VALIDATED")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FaceProfile(Base):
    __tablename__ = "face_profiles"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_member_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("family_members.id", ondelete="CASCADE"),
    )
    display_name: Mapped[str] = mapped_column(String(100))
    image_ref: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    consent_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    match_score: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(30), default="VALIDATED")
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoVerificationRequest(Base):
    __tablename__ = "video_verification_requests"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"))
    family_member_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("family_members.id", ondelete="CASCADE"),
    )
    risk_event_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("risk_events.id"))
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED")
    match_score: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(30), default="WAITING")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CallEvent(Base):
    __tablename__ = "call_events"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"))
    phone_number_hash: Mapped[str] = mapped_column(Text)
    phone_number_last4: Mapped[str] = mapped_column(String(4))
    direction: Mapped[str] = mapped_column(String(20))
    caller_type: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    action_taken: Mapped[str | None] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CallSession(Base):
    __tablename__ = "call_sessions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"))
    call_event_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("call_events.id"))
    caller_number_hash: Mapped[str] = mapped_column(Text, index=True)
    caller_number_last4: Mapped[str] = mapped_column(String(4))
    direction: Mapped[str] = mapped_column(String(20), default="INCOMING")
    family_number_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_family_member_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("family_members.id"),
    )
    suspected: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class FamilyConfirmation(Base):
    __tablename__ = "family_confirmations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    call_session_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    family_member_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("family_members.id"))
    guardian_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("guardians.id"))
    notification_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("emergency_notifications.id"),
    )
    channel: Mapped[str] = mapped_column(String(20), default="PUSH")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    response: Mapped[str | None] = mapped_column(String(30))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DevicePushToken(Base):
    __tablename__ = "device_push_tokens"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    guardian_id: Mapped[str] = mapped_column(GUID(), ForeignKey("guardians.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(String(20), default="ANDROID")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PushDelivery(Base):
    __tablename__ = "push_deliveries"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    confirmation_id: Mapped[str] = mapped_column(GUID(), ForeignKey("family_confirmations.id", ondelete="CASCADE"), index=True)
    push_token_id: Mapped[str] = mapped_column(GUID(), ForeignKey("device_push_tokens.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskDecision(Base):
    __tablename__ = "risk_decisions"
    __table_args__ = (
        UniqueConstraint("call_session_id", "sequence", name="uq_risk_decision_session_sequence"),
    )

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    call_session_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    number_mismatch: Mapped[bool] = mapped_column(Boolean, default=True)
    speaker_similarity: Mapped[float | None] = mapped_column(Float)
    spoof_probability: Mapped[float | None] = mapped_column(Float)
    content_risk_score: Mapped[int | None] = mapped_column(Integer)
    family_response: Mapped[str | None] = mapped_column(String(30))
    face_match_score: Mapped[int | None] = mapped_column(Integer)
    voice_profile_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("voice_profiles.id"))
    transcript: Mapped[str | None] = mapped_column(Text)
    transcript_language: Mapped[str | None] = mapped_column(String(20))
    transcript_confidence: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str] = mapped_column(String(30))
    reason_codes: Mapped[str] = mapped_column(Text, default="")
    policy_version: Mapped[str] = mapped_column(String(50), default="patent-v1")
    model_versions_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResponseAction(Base):
    __tablename__ = "response_actions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    call_session_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    risk_decision_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("risk_decisions.id", ondelete="CASCADE"),
    )
    action: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    failure_reason: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskNumber(Base):
    __tablename__ = "risk_numbers"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    phone_number_hash: Mapped[str] = mapped_column(Text, index=True)
    phone_number_last4: Mapped[str] = mapped_column(String(4))
    label: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(50), default="MANUAL")
    risk_score: Mapped[int] = mapped_column(Integer, default=80)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    senior_id: Mapped[str] = mapped_column(GUID(), ForeignKey("seniors.id", ondelete="CASCADE"))
    call_event_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("call_events.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20))
    reason_codes: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmergencyNotification(Base):
    __tablename__ = "emergency_notifications"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    risk_event_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("risk_events.id", ondelete="CASCADE"),
    )
    guardian_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("guardians.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    response: Mapped[str | None] = mapped_column(String(30))
    message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    consent_type: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(30))
    accepted: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(GUID())
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
