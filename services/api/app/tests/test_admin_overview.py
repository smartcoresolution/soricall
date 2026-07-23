from sqlalchemy import select

from app.api.v1.admin import get_admin_overview
from app.core.database import SessionLocal
from app.models import AuditLog, Senior
from app.tests.factories import register_test_user


def test_admin_overview_masks_personal_data_and_writes_audit_log() -> None:
    db = SessionLocal()
    auth = register_test_user(db, display_name="김관리대상", role="SENIOR")
    senior = db.scalar(select(Senior).where(Senior.user_id == auth.user.id))
    assert senior is not None
    overview = get_admin_overview(db)
    row = next(item for item in overview["seniors"] if item["id"] == senior.id)
    assert row["name"] == "김****"
    assert row["phone"].startswith("010-****-")
    assert db.scalar(select(AuditLog).where(AuditLog.action == "ADMIN_OVERVIEW_VIEW")) is not None
    db.close()
