"""Role gates used by routers: engineer writes, analyst annotates/exports, viewer reads."""
from fastapi import Depends

from src.constants.error_codes import AppError, ErrorCode
from src.constants.enums import Role
from src.middlewares.auth import get_current_user
from src.models import User

ENGINEER = Role.ENGINEER.value
ANALYST = Role.ANALYST.value
VIEWER = Role.VIEWER.value

READ_ROLES = (ENGINEER, ANALYST, VIEWER)
EXPORT_ROLES = (ENGINEER, ANALYST)
ANNOTATE_ROLES = (ENGINEER, ANALYST)
WRITE_ROLES = (ENGINEER,)


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(
                ErrorCode.FORBIDDEN,
                f"当前角色 {user.role} 无权执行该操作，需要 {'/'.join(roles)}",
                status_code=403,
                detail={"required_roles": list(roles), "role": user.role},
            )
        return user

    return dependency
