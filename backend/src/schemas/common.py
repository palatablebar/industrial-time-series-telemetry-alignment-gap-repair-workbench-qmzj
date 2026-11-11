"""Shared response envelopes."""
from typing import Any

from pydantic import BaseModel


def error_envelope(code: str, message: str, request_id: str | None = None, detail: Any = None) -> dict:
    return {
        "code": code,
        "message": message,
        "detail": detail or {},
        "request_id": request_id,
    }


class PagedMeta(BaseModel):
    total: int
    returned: int
