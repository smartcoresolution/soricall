from app.api.v1.admin import create_risk_number
from app.api.v1.auth import register
from app.api.v1.families import add_family_member, create_family, upsert_safe_word
from app.api.v1.seniors import add_guardian, create_senior
from app.api.v1.voice_profiles import add_voice_sample, create_voice_profile, enroll_voice_profile
from app.core.database import Base, SessionLocal, engine
from app.models import User
from app.schemas import (
    FamilyCreate,
    FamilyMemberCreate,
    GuardianCreate,
    RegisterRequest,
    RiskNumberCreate,
    SafeWordUpsert,
    SeniorCreate,
    VoiceEnrollRequest,
    VoiceProfileCreate,
    VoiceSampleCreate,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "guardian.demo@example.com").first():
            print("Demo data already exists.")
            return

        guardian = register(
            RegisterRequest(
                email="guardian.demo@example.com",
                password="password123",
                display_name="데모 보호자",
                role="GUARDIAN",
                phone_number="+821055550001",
            ),
            db,
        )
        family = create_family(FamilyCreate(name="데모 가족", created_by=guardian.user.id), db)
        family_member = add_family_member(
            family.id,
            FamilyMemberCreate(
                name="김민수",
                relation="아들",
                phone_number="+821012345678",
            ),
            db,
        )
        senior = create_senior(
            SeniorCreate(
                family_id=family.id,
                name="김영희",
                phone_number="+821099998888",
                birth_year=1948,
            ),
            db,
        )
        add_guardian(
            senior.id,
            GuardianCreate(user_id=guardian.user.id, relation="DAUGHTER"),
            db,
        )
        upsert_safe_word(
            family.id,
            SafeWordUpsert(word="청포도", hint="우리 가족 과일"),
            db,
        )
        create_risk_number(
            RiskNumberCreate(
                phone_number="+821077770000",
                label="데모 위험번호",
                risk_score=90,
            ),
            db,
        )
        voice_profile = create_voice_profile(
            VoiceProfileCreate(
                family_member_id=family_member.id,
                display_name="김민수 목소리",
            ),
            db,
        )
        add_voice_sample(
            voice_profile.id,
            VoiceSampleCreate(
                audio_ref="family-clean-sample.wav",
                object_key="demo/family-clean-sample.wav",
                duration_ms=5000,
                sample_rate=16000,
                mime_type="audio/wav",
            ),
            db,
        )
        enroll_voice_profile(
            voice_profile.id,
            VoiceEnrollRequest(audio_ref="family-clean-sample.wav"),
            db,
        )

        print("Demo data created.")
        print("Guardian login: guardian.demo@example.com / password123")
        print(f"Family ID: {family.id}")
        print(f"Senior ID: {senior.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
