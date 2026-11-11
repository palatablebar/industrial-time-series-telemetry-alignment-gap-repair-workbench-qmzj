"""Authentication, daily quota reset and role helpers."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.error_codes import AppError, ErrorCode
from src.constants.enums import Role
from src.models import User
from src.utils.jwt import create_access_token
from src.utils.password import verify_password

WRITE_ROLES = (Role.ENGINEER.value,)


def reset_daily_quota_if_needed(db: Session, user: User) -> None:
    today = date.today()
    if user.quota_used_date != today:
        user.quota_used_date = today
        user.quota_used = 0
        db.commit()


def authenticate(db: Session, email: str, password: str) -> tuple[str, User]:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.UNAUTHORIZED, "邮箱或密码不正确", status_code=401)
    reset_daily_quota_if_needed(db, user)
    token = create_access_token(user)
    return token, user


def quota_snapshot(user: User, daily_limit: int) -> dict:
    return {
        "daily_quota": daily_limit,
        "quota_used": int(user.quota_used or 0),
        "quota_remaining": max(0, daily_limit - int(user.quota_used or 0)),
        "date": (user.quota_used_date or date.today()).strftime("%Y-%m-%d"),
    }
