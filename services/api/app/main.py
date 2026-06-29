from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, calls, emergency, face_video, families, risk_events, seniors, voice_profiles
from app.core.config import get_settings
from app.core.database import init_db


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


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(families.router, prefix="/api/v1")
app.include_router(seniors.router, prefix="/api/v1")
app.include_router(calls.router, prefix="/api/v1")
app.include_router(risk_events.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(emergency.router, prefix="/api/v1")
app.include_router(voice_profiles.router, prefix="/api/v1")
app.include_router(face_video.router, prefix="/api/v1")
