from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: str
    email: str | None
    display_name: str
    role: str

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(SENIOR|GUARDIAN|FAMILY_MEMBER|ADMIN)$")
    phone_number: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    created_by: str | None = None


class FamilyResponse(BaseModel):
    id: str
    name: str
    created_by: str | None

    model_config = {"from_attributes": True}


class FamilyMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    relation: str | None = None
    phone_number: str | None = None
    user_id: str | None = None


class FamilyMemberResponse(BaseModel):
    id: str
    family_id: str
    name: str
    relation: str | None
    phone_number_last4: str | None
    is_verified: bool

    model_config = {"from_attributes": True}


class SeniorCreate(BaseModel):
    family_id: str
    name: str = Field(min_length=1, max_length=100)
    phone_number: str | None = None
    birth_year: int | None = None
    user_id: str | None = None


class SeniorResponse(BaseModel):
    id: str
    family_id: str
    name: str
    phone_number_last4: str | None
    birth_year: int | None

    model_config = {"from_attributes": True}


class GuardianCreate(BaseModel):
    user_id: str
    relation: str | None = None
    priority: int = 1
    notify_enabled: bool = True


class GuardianResponse(BaseModel):
    id: str
    senior_id: str
    user_id: str
    relation: str | None
    priority: int
    notify_enabled: bool

    model_config = {"from_attributes": True}


class SafeWordUpsert(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    hint: str | None = Field(default=None, max_length=255)
    updated_by: str | None = None


class SafeWordResponse(BaseModel):
    id: str
    family_id: str
    hint: str | None

    model_config = {"from_attributes": True}


class SafeWordVerifyRequest(BaseModel):
    word: str = Field(min_length=1, max_length=100)


class SafeWordVerifyResponse(BaseModel):
    matched: bool


class VoiceProfileCreate(BaseModel):
    family_member_id: str
    display_name: str = Field(min_length=1, max_length=100)
    consent_id: str | None = None


class VoiceProfileResponse(BaseModel):
    id: str
    family_member_id: str
    display_name: str
    status: str
    embedding_model: str | None
    embedding_version: str | None
    quality_score: int | None

    model_config = {"from_attributes": True}


class VoiceSampleCreate(BaseModel):
    audio_ref: str = Field(min_length=1)
    object_key: str | None = None
    duration_ms: int | None = None
    sample_rate: int | None = None
    mime_type: str | None = None
    purpose: str = Field(default="ENROLLMENT", pattern="^(ENROLLMENT|ANALYSIS)$")


class VoiceSampleResponse(BaseModel):
    id: str
    voice_profile_id: str
    object_key: str | None
    audio_ref: str | None
    purpose: str
    retained: bool

    model_config = {"from_attributes": True}


class VoiceEnrollRequest(BaseModel):
    audio_ref: str | None = None


class VoiceEnrollResponse(BaseModel):
    id: str
    status: str
    embedding_model: str | None
    embedding_version: str | None
    quality_score: int | None


class FaceProfileCreate(BaseModel):
    family_member_id: str
    display_name: str = Field(min_length=1, max_length=100)
    image_ref: str | None = None
    consent_accepted: bool = False


class FaceProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    image_ref: str | None = None
    consent_accepted: bool | None = None
    match_score: int | None = Field(default=None, ge=0, le=100)


class FaceProfileResponse(BaseModel):
    id: str
    family_member_id: str
    display_name: str
    image_ref: str | None
    status: str
    consent_accepted: bool
    match_score: int | None

    model_config = {"from_attributes": True}


class VideoVerificationCreate(BaseModel):
    senior_id: str
    family_member_id: str
    risk_event_id: str | None = None


class VideoVerificationAccept(BaseModel):
    match_score: int = Field(default=88, ge=0, le=100)


class VideoVerificationResponse(BaseModel):
    id: str
    senior_id: str
    family_member_id: str
    risk_event_id: str | None
    status: str
    match_score: int | None
    result: str

    model_config = {"from_attributes": True}


class CallEvaluateRequest(BaseModel):
    senior_id: str
    phone_number: str = Field(min_length=1)
    direction: str = Field(pattern="^(INCOMING|OUTGOING)$")


class CallEvaluateResponse(BaseModel):
    call_event_id: str
    risk_score: int
    risk_level: str
    caller_type: str
    action_recommended: str
    reason_codes: list[str]
    message_for_senior: str


class RiskNumberCreate(BaseModel):
    phone_number: str = Field(min_length=1)
    label: str | None = Field(default=None, max_length=100)
    source: str = Field(default="MANUAL", max_length=50)
    risk_score: int = Field(default=80, ge=31, le=100)


class RiskNumberResponse(BaseModel):
    id: str
    phone_number_last4: str
    label: str | None
    source: str
    risk_score: int
    active: bool

    model_config = {"from_attributes": True}


class RiskEventCreate(BaseModel):
    senior_id: str
    call_event_id: str | None = None
    event_type: str = Field(min_length=1, max_length=50)
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    reason_codes: list[str] = []
    summary: str | None = None


class RiskEventResponse(BaseModel):
    id: str
    senior_id: str
    call_event_id: str | None
    event_type: str
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    summary: str | None


class EmergencyConfirmFamilyCallRequest(BaseModel):
    senior_id: str
    call_event_id: str | None = None
    risk_event_id: str | None = None
    message: str = "가족 사칭 의심 전화입니다. 실제 가족 통화인지 확인해 주세요."


class EmergencyNotifyRequest(BaseModel):
    risk_event_id: str
    message: str = "부모님이 가족 사칭 의심 전화를 받고 있습니다."


class EmergencyNotifyResponse(BaseModel):
    emergency_event_id: str
    notified_guardians: int
    status: str


class EmergencyNotificationResponse(BaseModel):
    id: str
    risk_event_id: str
    guardian_id: str
    status: str
    response: str | None
    message: str | None

    model_config = {"from_attributes": True}


class EmergencyRespondRequest(BaseModel):
    notification_id: str
    response: str = Field(pattern="^(REAL_CALL|NOT_ME|UNKNOWN)$")


class EmergencyRespondResponse(BaseModel):
    notification_id: str
    status: str
    response: str
