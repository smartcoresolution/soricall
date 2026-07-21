from datetime import datetime

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: str
    email: str | None
    display_name: str
    role: str
    phone_number: str | None = None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    phone_number: str = Field(pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")
    verification_token: str = Field(min_length=1)
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(SENIOR|GUARDIAN|FAMILY_MEMBER|ADMIN)$")


class LoginRequest(BaseModel):
    phone_number: str = Field(pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")
    password: str


class PhoneVerificationSendRequest(BaseModel):
    phone_number: str = Field(pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")


class PhoneVerificationSendResponse(BaseModel):
    verification_id: str
    expires_in: int
    development_code: str | None = None


class PhoneVerificationConfirmRequest(BaseModel):
    verification_id: str
    code: str = Field(pattern=r"^\d{6}$")


class PhoneVerificationConfirmResponse(BaseModel):
    verification_token: str


class DeviceEnrollmentResponse(BaseModel):
    id: str
    protected_user_id: str
    protected_user_name: str
    phone_number_last4: str | None
    status: str
    enrollment_url: str | None = None
    access_token: str | None = None


class DeviceVerificationRequest(BaseModel):
    phone_number: str = Field(pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")


class DeviceVerificationConfirmRequest(BaseModel):
    verification_id: str
    code: str = Field(pattern=r"^\d{6}$")


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic
    family_id: str | None = None
    senior_id: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


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


class ScreeningCacheResponse(BaseModel):
    version: str
    generated_at: datetime
    family_number_hashes: list[str]
    risk_number_hashes: list[str]


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


class ProtectedCallUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    relation_code: str = Field(pattern="^(SELF|FATHER|MOTHER|PATERNAL_GRANDFATHER|PATERNAL_GRANDMOTHER|MATERNAL_GRANDFATHER|MATERNAL_GRANDMOTHER|SPOUSE_FATHER|SPOUSE_MOTHER|OTHER)$")
    phone_number: str = Field(min_length=4)
    user_id: str | None = None


class ProtectedCallUserResponse(BaseModel):
    id: str
    family_id: str
    name: str
    member_type: str
    relation_code: str
    phone_number_last4: str | None
    protection_status: str

    model_config = {"from_attributes": True}


class ConfirmationContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    relation_code: str = Field(pattern="^(SON|DAUGHTER|GRANDSON|GRANDDAUGHTER|SPOUSE|OTHER)$")
    phone_number: str = Field(min_length=4)
    user_id: str | None = None
    is_primary_contact: bool = False
    notification_priority: int = Field(default=1, ge=1, le=10)
    notify_enabled: bool = True


class ConfirmationContactResponse(BaseModel):
    id: str
    family_id: str
    protected_user_id: str
    name: str
    member_type: str
    relation_code: str | None
    phone_number_last4: str | None
    is_primary_contact: bool
    notification_priority: int
    notify_enabled: bool
    approval_status: str
    trust_level: str

    model_config = {"from_attributes": True}


class EnrollmentInvitationResponse(BaseModel):
    id: str
    family_id: str
    family_member_id: str
    family_member_name: str
    relation_code: str | None
    phone_number_last4: str | None
    channel: str
    requested_assets: list[str]
    status: str
    sent_at: str
    expires_at: str
    enrollment_url: str | None = None
    member_approval_status: str
    member_trust_level: str
    phone_verified: bool

    model_config = {"from_attributes": True}


class EnrollmentCompleteRequest(BaseModel):
    audio_ref: str = Field(min_length=1)
    duration_ms: int = Field(ge=1)
    mime_type: str = Field(default="audio/webm", min_length=1)
    face_image_ref: str | None = None
    consent_accepted: bool


class MediaImportSessionCreate(BaseModel):
    family_id: str
    family_member_id: str
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    source: str = Field(default="EXTERNAL_SHARE", pattern="^(EXTERNAL_SHARE|FILE_PICKER)$")


class MediaImportValidate(BaseModel):
    data_url: str = Field(min_length=1)


class MediaImportConsent(BaseModel):
    accepted: bool


class MediaImportSessionResponse(BaseModel):
    id: str
    family_id: str
    family_member_id: str
    source: str
    filename: str
    declared_mime_type: str
    detected_mime_type: str | None
    size_bytes: int | None
    status: str
    trust_level: str
    failure_code: str | None
    quality_status: str
    phone_verified_at: datetime | None
    consented_at: datetime | None
    expires_at: datetime

    model_config = {"from_attributes": True}


class DeviceKeyRegister(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    public_key_der_b64: str = Field(min_length=1)
    algorithm: str = Field(default="ECDSA_P256_SHA256", pattern="^ECDSA_P256_SHA256$")


class DeviceKeyResponse(BaseModel):
    id: str
    device_id: str
    algorithm: str
    fingerprint: str
    active: bool

    model_config = {"from_attributes": True}


class QrChallengeCreate(BaseModel):
    invitation_id: str
    nonce: str = Field(min_length=20)
    device_key_id: str


class QrChallengeResponse(BaseModel):
    challenge_id: str
    invitation_id: str
    challenge: str
    expires_at: datetime


class QrChallengeVerify(BaseModel):
    challenge: str = Field(min_length=20)
    signature_b64: str = Field(min_length=1)


class QrChallengeVerifyResponse(BaseModel):
    invitation_id: str
    device_key_id: str
    verified: bool
    verified_at: datetime


class DirectLivenessResponse(BaseModel):
    invitation_id: str
    action: str
    expires_at: datetime


class DirectLivenessVerify(BaseModel):
    observed_actions: list[str] = Field(min_length=1)
    capture_duration_ms: int = Field(ge=2000, le=30000)


class DirectLivenessVerifyResponse(BaseModel):
    invitation_id: str
    verified: bool
    verified_at: datetime


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
    content_hash: str | None
    size_bytes: int | None
    validation_status: str
    deleted_at: datetime | None = None

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
    size_bytes: int | None
    validation_status: str
    consented_at: datetime | None
    deleted_at: datetime | None

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


class CallSessionCreate(BaseModel):
    senior_id: str
    phone_number: str = Field(min_length=1)
    direction: str = Field(default="INCOMING", pattern="^(INCOMING|OUTGOING)$")


class CallSessionCreateResponse(BaseModel):
    call_session_id: str
    family_number_matched: bool
    matched_family_member_id: str | None
    suspected: bool
    status: str
    risk_decision_id: str
    risk_score: int
    risk_level: str
    decision: str
    reason_codes: list[str]
    response_action_id: str


class CallAnalysisSubmit(BaseModel):
    speaker_similarity: float = Field(ge=0, le=1)
    spoof_probability: float = Field(ge=0, le=1)
    content_risk_score: int = Field(ge=0, le=100)
    content_reason_codes: list[str] = Field(default_factory=list)
    face_match_score: int | None = Field(default=None, ge=0, le=100)
    model_versions: dict[str, str] = Field(default_factory=dict)


class CallAnalysisSubmitResponse(BaseModel):
    call_session_id: str
    risk_decision_id: str
    sequence: int
    risk_score: int
    risk_level: str
    decision: str
    reason_codes: list[str]
    response_action_id: str


class CallVoiceAnalysisRequest(BaseModel):
    voice_profile_id: str
    audio_ref: str = Field(min_length=1)


class CallVoiceAnalysisResponse(CallAnalysisSubmitResponse):
    transcript: str
    transcript_language: str
    transcript_confidence: float
    speaker_similarity: float
    spoof_probability: float


class ResponseActionResult(BaseModel):
    status: str = Field(pattern="^(EXECUTED|FAILED|SKIPPED)$")
    failure_reason: str | None = None


class ResponseActionResultResponse(BaseModel):
    response_action_id: str
    call_session_id: str
    action: str
    status: str
    failure_reason: str | None

    model_config = {"from_attributes": True}


class FamilyConfirmationCreate(BaseModel):
    family_member_id: str | None = None
    guardian_id: str | None = None
    channel: str = Field(default="PUSH", pattern="^(PUSH|SMS|CALL)$")
    expires_in_seconds: int = Field(default=300, ge=30, le=3600)


class FamilyConfirmationCreateResponse(BaseModel):
    confirmation_id: str
    call_session_id: str
    status: str
    channel: str
    expires_at: str


class FamilyConfirmationRespond(BaseModel):
    response: str = Field(pattern="^(CALLED|NOT_CALLED|UNKNOWN)$")


class FamilyConfirmationRespondResponse(BaseModel):
    confirmation_id: str
    call_session_id: str
    status: str
    response: str
    risk_decision_id: str
    risk_score: int
    risk_level: str
    decision: str
    reason_codes: list[str]
    response_action_id: str


class PushTokenRegister(BaseModel):
    token: str = Field(min_length=1)
    platform: str = Field(default="ANDROID", pattern="^(ANDROID|IOS|WEB)$")


class PushTokenResponse(BaseModel):
    id: str
    guardian_id: str
    platform: str
    active: bool


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
