from app.api.v1.auth import register
from app.api.v1.families import create_family
from app.api.v1.seniors import add_guardian, create_senior
from app.core.authorization import can_access_senior
from app.core.database import Base, SessionLocal, engine
from app.schemas import FamilyCreate, GuardianCreate, RegisterRequest, SeniorCreate


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_only_linked_guardian_can_access_senior() -> None:
    db = SessionLocal()
    linked = register(RegisterRequest(email="linked@example.com", password="password123", display_name="연결 보호자", role="GUARDIAN"), db).user
    stranger = register(RegisterRequest(email="stranger@example.com", password="password123", display_name="다른 보호자", role="GUARDIAN"), db).user
    family = create_family(FamilyCreate(name="권한 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    add_guardian(senior.id, GuardianCreate(user_id=linked.id), db)

    assert can_access_senior(db, linked, senior.id) is True
    assert can_access_senior(db, stranger, senior.id) is False
    db.close()
