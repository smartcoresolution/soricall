import uuid
from datetime import datetime

from sqlalchemy import Boolean, CHAR, DateTime, ForeignKey, Integer, String, Text, TypeDecorator, func
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
    phone_number: Mapped[str | None] = mapped_column(String(50))
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    relation: Mapped[str | None] = mapped_column(String(50))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    phone_number_hash: Mapped[str | None] = mapped_column(Text)
    phone_number_last4: Mapped[str | None] = mapped_column(String(4))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Senior(Base):
    __tablename__ = "seniors"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=new_uuid)
    family_id: Mapped[str] = mapped_column(GUID(), ForeignKey("families.id", ondelete="CASCADE"))
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
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
