import pytest
from fastapi import HTTPException

from app.api.v1.auth import refresh_access_token
from app.core.database import Base, SessionLocal, engine
from app.models import RefreshToken
from app.schemas import RefreshTokenRequest
from app.tests.factories import register_test_user


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_refresh_token_is_rotated_and_old_token_is_rejected() -> None:
    db = SessionLocal()
    registered = register_test_user(db, display_name="보호자")
    refreshed = refresh_access_token(
        RefreshTokenRequest(refresh_token=registered.refresh_token),
        db,
    )

    assert refreshed.access_token != registered.access_token
    assert refreshed.refresh_token != registered.refresh_token
    assert db.query(RefreshToken).filter(RefreshToken.revoked_at.is_not(None)).count() == 1

    with pytest.raises(HTTPException) as exc_info:
        refresh_access_token(RefreshTokenRequest(refresh_token=registered.refresh_token), db)
    assert exc_info.value.status_code == 401
    db.close()
