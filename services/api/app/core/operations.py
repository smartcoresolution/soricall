import json
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings


logger = logging.getLogger("soricall.request")
_requests: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def request_trace_id(request: Request) -> str:
    supplied = request.headers.get("x-request-id", "")
    return supplied[:128] if supplied and all(char.isalnum() or char in "-_." for char in supplied) else str(uuid4())


def rate_limit_response(request: Request, trace_id: str) -> JSONResponse | None:
    if request.url.path in {"/health", "/ready"}:
        return None
    settings = get_settings()
    sensitive = (
        request.url.path.startswith("/api/v1/auth/")
        or "phone-verification" in request.url.path
    )
    limit = settings.auth_rate_limit_per_minute if sensitive else settings.rate_limit_per_minute
    if settings.app_env == "development":
        limit *= 10
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    client = forwarded or (request.client.host if request.client else "unknown")
    key = f"{client}:{'sensitive' if sensitive else 'general'}"
    now = time.monotonic()
    with _rate_lock:
        bucket = _requests[key]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "trace_id": trace_id},
                headers={"Retry-After": "60", "X-Request-ID": trace_id},
            )
        bucket.append(now)
    return None


def log_request(*, trace_id: str, request: Request, status_code: int, elapsed_ms: float) -> None:
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
            ensure_ascii=False,
        )
    )
