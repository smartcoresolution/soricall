from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from sqlalchemy import text
import time
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    admin,
    auth,
    call_sessions,
    calls,
    device_enrollments,
    emergency,
    face_video,
    media_assets,
    qr_enrollment,
    families,
    risk_events,
    seniors,
    voice_profiles,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.authorization import DevicePrincipal, PROTECTED_PREFIXES, authenticate_request, authorized_for_request, current_user_id
from app.core.operations import log_request, rate_limit_response, request_trace_id


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="SoriCall API",
    description="Backend API for 안심소리 가족콜 / SoriCall.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def operations_and_security(request: Request, call_next):
    trace_id = request_trace_id(request)
    limited = rate_limit_response(request, trace_id)
    if limited:
        return limited
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    log_request(
        trace_id=trace_id,
        request=request,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response

if settings.app_env != "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def development_cors(request: Request, call_next):
    if settings.app_env != "development":
        return await call_next(request)

    origin = request.headers.get("origin")
    if request.method == "OPTIONS" and origin:
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "access-control-request-headers",
            "authorization,content-type",
        )
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
    return response


@app.middleware("http")
async def patent_api_authorization(request: Request, call_next):
    if (
        request.method == "OPTIONS"
        or
        not request.url.path.startswith(PROTECTED_PREFIXES)
        or request.url.path.startswith("/api/v1/auth/")
        or request.url.path.startswith("/api/v1/device-enrollments/")
        or request.url.path.startswith("/api/v1/enrollment-invitations/")
    ):
        return await call_next(request)
    db = SessionLocal()
    try:
        user = authenticate_request(request, db)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
        if not await authorized_for_request(request, db, user):
            return JSONResponse(status_code=403, content={"detail": "family access denied"})
        request.state.current_user_id = None if isinstance(user, DevicePrincipal) else user.id
        # Authorization is complete; do not keep a read transaction open while
        # the endpoint writes through its own database session (notably SQLite in dev/tests).
        db.close()
        context_token = current_user_id.set(None if isinstance(user, DevicePrincipal) else user.id)
        try:
            return await call_next(request)
        finally:
            current_user_id.reset(context_token)
    finally:
        db.close()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
    return {"status": "ready", "database": "ok"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(device_enrollments.family_router, prefix="/api/v1")
app.include_router(device_enrollments.public_router, prefix="/api/v1")
app.include_router(families.router, prefix="/api/v1")
app.include_router(families.enrollment_router, prefix="/api/v1")
app.include_router(seniors.router, prefix="/api/v1")
app.include_router(calls.router, prefix="/api/v1")
app.include_router(call_sessions.router, prefix="/api/v1")
app.include_router(call_sessions.confirmation_router, prefix="/api/v1")
app.include_router(call_sessions.push_router, prefix="/api/v1")
app.include_router(call_sessions.device_push_router, prefix="/api/v1")
app.include_router(risk_events.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(emergency.router, prefix="/api/v1")
app.include_router(voice_profiles.router, prefix="/api/v1")
app.include_router(face_video.router, prefix="/api/v1")
app.include_router(media_assets.router, prefix="/api/v1")
app.include_router(qr_enrollment.device_router, prefix="/api/v1")
app.include_router(qr_enrollment.qr_router, prefix="/api/v1")
