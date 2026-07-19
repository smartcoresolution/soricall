import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import FamilyMember, VoiceProfile, VoiceSample
from app.services.ai_client import AIClient


@dataclass(frozen=True)
class VoiceSampleValidation:
    content_hash: str | None
    size_bytes: int | None
    status: str


class VoiceProfileService:
    ALLOWED_MIME_TYPES = {
        "audio/webm",
        "audio/mp4",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/ogg",
    }
    MAX_SAMPLE_BYTES = 20 * 1024 * 1024
    MIN_ENROLLMENT_DURATION_MS = 15_000

    def __init__(self, db: Session, ai_client: AIClient | None = None):
        self.db = db
        self.ai_client = ai_client or AIClient()
        self.settings = get_settings()

    def create_profile(
        self,
        *,
        family_member_id: str,
        display_name: str,
        consent_id: str | None = None,
    ) -> VoiceProfile:
        if not self.db.get(FamilyMember, family_member_id):
            raise ValueError("family member not found")

        profile = VoiceProfile(
            family_member_id=family_member_id,
            display_name=display_name,
            consent_id=consent_id,
            status="PENDING",
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def add_sample(
        self,
        *,
        voice_profile_id: str,
        audio_ref: str,
        object_key: str | None,
        duration_ms: int | None,
        sample_rate: int | None,
        mime_type: str | None,
        purpose: str,
    ) -> VoiceSample:
        if not self.db.get(VoiceProfile, voice_profile_id):
            raise ValueError("voice profile not found")

        validation = self.validate_sample(
            audio_ref=audio_ref,
            duration_ms=duration_ms,
            mime_type=mime_type,
            purpose=purpose,
        )
        if validation.content_hash and self.db.scalar(
            select(VoiceSample.id).where(
                VoiceSample.voice_profile_id == voice_profile_id,
                VoiceSample.content_hash == validation.content_hash,
            )
        ):
            raise ValueError("duplicate voice sample")

        retained = self.settings.retain_voice_samples
        sample = VoiceSample(
            voice_profile_id=voice_profile_id,
            audio_ref=audio_ref if retained else None,
            object_key=object_key if retained else None,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            mime_type=mime_type,
            purpose=purpose,
            retained=retained,
            content_hash=validation.content_hash,
            size_bytes=validation.size_bytes,
            validation_status=validation.status,
            deleted_at=None if retained else datetime.now(timezone.utc),
        )
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def validate_sample(
        self,
        *,
        audio_ref: str,
        duration_ms: int | None,
        mime_type: str | None,
        purpose: str,
    ) -> VoiceSampleValidation:
        if purpose == "ENROLLMENT" and (duration_ms or 0) < self.MIN_ENROLLMENT_DURATION_MS:
            raise ValueError("VOICE_TOO_SHORT")
        normalized_mime = (mime_type or "").split(";", 1)[0].lower()
        if normalized_mime and normalized_mime not in self.ALLOWED_MIME_TYPES:
            raise ValueError("FILE_UNSUPPORTED")
        if not audio_ref.startswith("data:"):
            if self.settings.app_env == "production":
                raise ValueError("production voice samples must be uploaded audio data")
            return VoiceSampleValidation(None, None, "DEVELOPMENT_REFERENCE")
        try:
            header, encoded = audio_ref.split(",", 1)
            if ";base64" not in header:
                raise ValueError("FILE_UNSUPPORTED")
            header_mime = header.removeprefix("data:").split(";", 1)[0].lower()
            if header_mime not in self.ALLOWED_MIME_TYPES:
                raise ValueError("FILE_UNSUPPORTED")
            if normalized_mime and header_mime != normalized_mime:
                raise ValueError("FILE_UNSUPPORTED")
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            if isinstance(exc, ValueError) and str(exc) == "FILE_UNSUPPORTED":
                raise
            raise ValueError("FILE_UNSUPPORTED") from exc
        if not payload or len(payload) > self.MAX_SAMPLE_BYTES:
            raise ValueError("FILE_TOO_LARGE" if payload else "FILE_UNSUPPORTED")
        return VoiceSampleValidation(
            content_hash=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            status="VALIDATED",
        )

    def enroll(self, *, voice_profile_id: str, audio_ref: str | None = None) -> VoiceProfile:
        profile = self.db.get(VoiceProfile, voice_profile_id)
        if not profile:
            raise ValueError("voice profile not found")

        sample_ref = audio_ref or self._latest_sample_ref(voice_profile_id)
        if not sample_ref:
            raise ValueError("voice sample not found")

        result = self.ai_client.enroll_voice(audio_ref=sample_ref)
        profile.embedding = result.embedding
        profile.embedding_model = result.model_name
        profile.embedding_version = result.model_version
        profile.quality_score = round(result.quality_score * 100)
        profile.status = "ENROLLED"
        profile.enrolled_at = datetime.now()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def _latest_sample_ref(self, voice_profile_id: str) -> str | None:
        sample = self.db.scalar(
            select(VoiceSample)
            .where(VoiceSample.voice_profile_id == voice_profile_id)
            .order_by(VoiceSample.created_at.desc())
        )
        if not sample:
            return None
        return sample.audio_ref or sample.object_key
