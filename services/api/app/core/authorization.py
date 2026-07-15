import json
from contextvars import ContextVar

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.models import CallSession, Family, FamilyConfirmation, FamilyMember, Guardian, Senior, User


PROTECTED_PREFIXES = ("/api/v1",)
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def authenticate_request(request: Request, db: Session) -> User | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if not payload or not payload.get("sub"):
        return None
    return db.get(User, str(payload["sub"]))


def can_access_senior(db: Session, user: User, senior_id: str) -> bool:
    if user.role == "ADMIN":
        return True
    senior = db.get(Senior, senior_id)
    if not senior:
        return False
    if senior.user_id == user.id:
        return True
    if db.scalar(select(Guardian.id).where(Guardian.senior_id == senior_id, Guardian.user_id == user.id)):
        return True
    return db.scalar(
        select(FamilyMember.id).where(
            FamilyMember.family_id == senior.family_id,
            FamilyMember.user_id == user.id,
        )
    ) is not None


def can_access_family(db: Session, user: User, family_id: str) -> bool:
    if user.role == "ADMIN":
        return True
    family = db.get(Family, family_id)
    if not family:
        return False
    if family.created_by == user.id:
        return True
    if db.scalar(
        select(FamilyMember.id).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user.id,
        )
    ):
        return True
    if db.scalar(select(Senior.id).where(Senior.family_id == family_id, Senior.user_id == user.id)):
        return True
    return db.scalar(
        select(Guardian.id)
        .join(Senior, Guardian.senior_id == Senior.id)
        .where(Senior.family_id == family_id, Guardian.user_id == user.id)
    ) is not None


async def authorized_for_request(request: Request, db: Session, user: User) -> bool:
    path = request.url.path
    if path.startswith("/api/v1/auth/"):
        return True
    if path.startswith("/api/v1/admin/"):
        return user.role == "ADMIN"
    if user.role == "ADMIN":
        return True
    if path == "/api/v1/families" and request.method == "POST":
        return user.role in {"GUARDIAN", "SENIOR", "FAMILY_MEMBER"}
    if path.startswith("/api/v1/families/"):
        parts = path.split("/")
        return len(parts) > 4 and can_access_family(db, user, parts[4])
    if path == "/api/v1/call-sessions" and request.method == "POST":
        try:
            senior_id = str(json.loads(await request.body())["senior_id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False
        return can_access_senior(db, user, senior_id)
    if path.startswith("/api/v1/call-sessions/"):
        session_id = path.split("/")[4]
        call_session = db.get(CallSession, session_id)
        return bool(call_session and can_access_senior(db, user, call_session.senior_id))
    if path.startswith("/api/v1/family-confirmations/"):
        confirmation_id = path.split("/")[4]
        confirmation = db.get(FamilyConfirmation, confirmation_id)
        if not confirmation:
            return False
        call_session = db.get(CallSession, confirmation.call_session_id)
        return bool(call_session and can_access_senior(db, user, call_session.senior_id))
    if path.startswith("/api/v1/guardians/"):
        guardian_id = path.split("/")[4]
        guardian = db.get(Guardian, guardian_id)
        return bool(
            guardian
            and (guardian.user_id == user.id or can_access_senior(db, user, guardian.senior_id))
        )
    if path.startswith("/api/v1/seniors/"):
        return can_access_senior(db, user, path.split("/")[4])
    if path == "/api/v1/seniors" and request.method == "POST":
        return user.role in {"GUARDIAN", "SENIOR", "ADMIN"}
    return user.role in {"SENIOR", "GUARDIAN", "FAMILY_MEMBER", "ADMIN"}
