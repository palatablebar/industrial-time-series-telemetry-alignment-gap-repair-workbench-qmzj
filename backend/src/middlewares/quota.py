"""Redis sliding-window rate limit + per-user daily job quota."""
import time
from datetime import date

import redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.constants.error_codes import AppError, ErrorCode
from src.models import User
from src.schemas.common import error_envelope
from src.utils.logger import log_event

_client = None
_memory_window: dict[str, list[float]] = {}


def get_redis():
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_timeout=0.4,
                socket_connect_timeout=0.4,
                decode_responses=True,
            )
            _client.ping()
        except Exception:
            _client = False
    return _client or None


def _memory_allow(key: str, now: float, window: int, max_hits: int) -> bool:
    hits = [stamp for stamp in _memory_window.get(key, []) if stamp > now - window]
    hits.append(now)
    _memory_window[key] = hits
    return len(hits) <= max_hits


def rate_limit_allow(user_id: int) -> bool:
    window = settings.RATE_WINDOW_SECONDS
    max_hits = settings.RATE_WINDOW_MAX
    now = time.time()
    key = f"rl:tsalign:{user_id}"
    client = get_redis()
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {f"{now:.6f}": now})
            pipe.zcard(key)
            pipe.expire(key, window)
            _, _, count, _ = pipe.execute()
            allowed = int(count) <= max_hits
        except Exception:
            allowed = _memory_allow(key, now, window, max_hits)
    else:
        allowed = _memory_allow(key, now, window, max_hits)
    if not allowed:
        log_event("RATE_LIMITED", user_id=user_id, window_max=max_hits)
    return allowed


def consume_job_quota(db, user: User) -> dict:
    today = date.today()
    if user.quota_used_date != today:
        user.quota_used_date = today
        user.quota_used = 0
    limit = int(user.daily_job_quota or settings.DAILY_JOB_QUOTA)
    if int(user.quota_used or 0) >= limit:
        log_event("QUOTA_REJECTED", user_id=user.id, used=user.quota_used, limit=limit)
        raise AppError(
            ErrorCode.QUOTA_EXHAUSTED,
            status_code=429,
            detail={"limit": limit, "used": user.quota_used},
        )
    user.quota_used = int(user.quota_used or 0) + 1
    db.commit()
    return {"limit": limit, "used": user.quota_used, "remaining": max(0, limit - user.quota_used)}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding window on write requests; 429 carries retry_after."""

    WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    async def dispatch(self, request, call_next):
        if request.method in self.WRITE_METHODS:
            claims = getattr(request.state, "user_claims", None) or {}
            user_id = claims.get("sub")
            if user_id and not rate_limit_allow(int(user_id)):
                return JSONResponse(
                    status_code=429,
                    content=error_envelope(
                        ErrorCode.RATE_LIMITED.value,
                        "请求过于频繁",
                        getattr(request.state, "request_id", None),
                        {"retry_after": settings.RATE_WINDOW_SECONDS},
                    ),
                )
        return await call_next(request)
