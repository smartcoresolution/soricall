import asyncio

from app.api.v1.families import create_family, list_accessible_families
from app.api.v1.seniors import add_guardian, create_senior
from app.core.authorization import authorized_for_request, can_access_family, can_access_senior, current_user_id
from app.core.database import Base, SessionLocal, engine
from app.schemas import FamilyCreate, GuardianCreate, SeniorCreate
from app.tests.factories import register_test_user
from starlette.requests import Request


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_only_linked_guardian_can_access_senior() -> None:
    db = SessionLocal()
    linked = register_test_user(db, display_name="연결 보호자").user
    stranger = register_test_user(db, display_name="다른 보호자").user
    family = create_family(FamilyCreate(name="권한 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    add_guardian(senior.id, GuardianCreate(user_id=linked.id), db)

    assert can_access_senior(db, linked, senior.id) is True
    assert can_access_senior(db, stranger, senior.id) is False
    db.close()


def test_only_linked_user_can_access_family() -> None:
    db = SessionLocal()
    owner = register_test_user(db, display_name="소유자").user
    linked = register_test_user(db, display_name="연결 가족", role="FAMILY_MEMBER").user
    stranger = register_test_user(db, display_name="외부인").user
    family = create_family(FamilyCreate(name="소유 가족", created_by=owner.id), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    add_guardian(senior.id, GuardianCreate(user_id=linked.id), db)

    assert can_access_family(db, owner, family.id) is True
    assert can_access_family(db, linked, family.id) is True
    assert can_access_family(db, stranger, family.id) is False
    db.close()


def test_family_route_uses_authenticated_owner_and_rejects_stranger() -> None:
    db = SessionLocal()
    owner = register_test_user(db, display_name="HTTP 소유자").user
    stranger = register_test_user(db, display_name="HTTP 외부인").user
    context_token = current_user_id.set(owner.id)
    try:
        family = create_family(FamilyCreate(name="HTTP 권한 가족", created_by=stranger.id), db)
    finally:
        current_user_id.reset(context_token)

    assert family.created_by == owner.id
    request = Request({"type": "http", "method": "GET", "path": f"/api/v1/families/{family.id}", "headers": [], "query_string": b"", "scheme": "http", "server": ("test", 80), "client": ("test", 123)})
    assert asyncio.run(authorized_for_request(request, db, stranger)) is False
    db.close()


def test_lists_only_families_accessible_to_current_user() -> None:
    db = SessionLocal()
    owner = register_test_user(db, display_name="목록 소유자").user
    stranger = register_test_user(db, display_name="목록 외부인").user
    owned = create_family(FamilyCreate(name="내 가족", created_by=owner.id), db)
    create_family(FamilyCreate(name="다른 가족", created_by=stranger.id), db)

    context_token = current_user_id.set(owner.id)
    try:
        accessible = list_accessible_families(db)
    finally:
        current_user_id.reset(context_token)

    assert [family.id for family in accessible] == [owned.id]
    db.close()
