from app.api.v1.families import (
    create_confirmation_contact,
    create_family,
    create_protected_call_user,
    list_confirmation_contacts,
    list_protected_call_users,
)
from app.core.database import Base, SessionLocal, engine
from app.schemas import (
    ConfirmationContactCreate,
    FamilyCreate,
    ProtectedCallUserCreate,
)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_registers_protected_parent_and_simple_confirmation_contacts() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="통화 보호 가족"), db)
    protected = create_protected_call_user(
        family.id,
        ProtectedCallUserCreate(
            name="김영희",
            relation_code="MOTHER",
            phone_number="010-1111-2222",
        ),
        db,
    )
    first = create_confirmation_contact(
        family.id,
        protected.id,
        ConfirmationContactCreate(
            name="김민지",
            relation_code="DAUGHTER",
            phone_number="010-3333-4444",
            is_primary_contact=True,
            notification_priority=1,
        ),
        db,
    )
    create_confirmation_contact(
        family.id,
        protected.id,
        ConfirmationContactCreate(
            name="김민수",
            relation_code="SON",
            phone_number="010-5555-6666",
            notification_priority=2,
        ),
        db,
    )

    assert protected.member_type == "PROTECTED_CALL_USER"
    assert protected.relation_code == "MOTHER"
    assert protected.protection_status == "PREPARING"
    assert first.member_type == "FAMILY_CONFIRMATION_CONTACT"
    assert first.phone_number is None
    assert len(list_protected_call_users(family.id, db)) == 1
    contacts = list_confirmation_contacts(family.id, protected.id, db)
    assert [contact.relation_code for contact in contacts] == ["DAUGHTER", "SON"]
    db.close()
