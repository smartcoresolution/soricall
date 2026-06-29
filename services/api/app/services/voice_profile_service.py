from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import FamilyMember, VoiceProfile, VoiceSample
from app.services.ai_client import AIClient


class VoiceProfileService:
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
        )
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

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

