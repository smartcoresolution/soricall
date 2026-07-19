import pytest
from fastapi import HTTPException

from app.api.v1.families import (
    approve_confirmation_contact,
    create_confirmation_contact,
    create_family,
    create_protected_call_user,
    delete_confirmation_contact,
    list_confirmation_contacts,
    list_protected_call_users,
    reverify_confirmation_contact,
    revoke_confirmation_contact,
)
from app.core.authorization import current_user_id
from app.core.database import Base, SessionLocal, engine
from app.models import AuditLog
from app.schemas import (
    ConfirmationContactCreate,
    FamilyCreate,
    ProtectedCallUserCreate,
)
from app.tests.factories import register_test_user


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
    assert first.protected_user_id == protected.id
    assert first.phone_number is None
    assert len(list_protected_call_users(family.id, db)) == 1
    contacts = list_confirmation_contacts(family.id, protected.id, db)
    assert [contact.relation_code for contact in contacts] == ["DAUGHTER", "SON"]
    delete_confirmation_contact(family.id, protected.id, first.id, db)
    contacts = list_confirmation_contacts(family.id, protected.id, db)
    assert [contact.relation_code for contact in contacts] == ["SON"]
    db.close()


def test_confirmation_contacts_are_isolated_by_protected_user() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="복수 보호 대상 가족"), db)
    mother = create_protected_call_user(
        family.id,
        ProtectedCallUserCreate(
            name="어머니",
            relation_code="MOTHER",
            phone_number="010-1111-1111",
        ),
        db,
    )
    father = create_protected_call_user(
        family.id,
        ProtectedCallUserCreate(
            name="아버지",
            relation_code="FATHER",
            phone_number="010-2222-2222",
        ),
        db,
    )
    mother_contact = create_confirmation_contact(
        family.id,
        mother.id,
        ConfirmationContactCreate(
            name="어머니 확인 가족",
            relation_code="DAUGHTER",
            phone_number="010-3333-3333",
        ),
        db,
    )
    father_contact = create_confirmation_contact(
        family.id,
        father.id,
        ConfirmationContactCreate(
            name="아버지 확인 가족",
            relation_code="SON",
            phone_number="010-4444-4444",
        ),
        db,
    )

    assert [contact.id for contact in list_confirmation_contacts(family.id, mother.id, db)] == [
        mother_contact.id
    ]
    assert [contact.id for contact in list_confirmation_contacts(family.id, father.id, db)] == [
        father_contact.id
    ]

    with pytest.raises(HTTPException) as error:
        delete_confirmation_contact(family.id, mother.id, father_contact.id, db)
    assert error.value.status_code == 404
    assert db.get(type(father_contact), father_contact.id) is not None
    db.close()


def test_protected_user_owner_controls_contact_approval_state() -> None:
    db = SessionLocal()
    owner_id = register_test_user(db, display_name="본인").user.id
    family = create_family(FamilyCreate(name="승인 상태 가족"), db)
    protected = create_protected_call_user(
        family.id,
        ProtectedCallUserCreate(
            name="본인",
            relation_code="SELF",
            phone_number="010-1111-1111",
            user_id=owner_id,
        ),
        db,
    )
    contact = create_confirmation_contact(
        family.id,
        protected.id,
        ConfirmationContactCreate(
            name="확인 가족",
            relation_code="DAUGHTER",
            phone_number="010-2222-2222",
        ),
        db,
    )
    contact.approval_status = "REVIEW_REQUIRED"
    contact.trust_level = "B"
    db.commit()

    token = current_user_id.set(owner_id)
    try:
        approved = approve_confirmation_contact(family.id, protected.id, contact.id, db)
        assert approved.approval_status == "ACTIVE"
        assert approved.is_verified is True
        assert approved.approved_by == owner_id

        reverify = reverify_confirmation_contact(family.id, protected.id, contact.id, db)
        assert reverify.approval_status == "REVERIFY"
        assert reverify.is_verified is False

        revoked = revoke_confirmation_contact(
            family.id,
            protected.id,
            contact.id,
            db,
            reason="사용자 요청",
        )
        assert revoked.approval_status == "REVOKED"
        assert revoked.revocation_reason == "사용자 요청"
    finally:
        current_user_id.reset(token)

    assert db.query(AuditLog).filter(AuditLog.resource_id == contact.id).count() == 3
    db.close()
