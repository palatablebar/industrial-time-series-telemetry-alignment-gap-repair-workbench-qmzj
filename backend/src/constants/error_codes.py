"""Stable error codes for the API envelope."""
from dataclasses import dataclass, field


class ErrorCode:
    UNAUTHORIZED = "TSA-1001"
    FORBIDDEN = "TSA-1002"
    RATE_LIMITED = "TSA-1003"
    QUOTA_EXHAUSTED = "TSA-1004"
    NOT_FOUND = "TSA-2001"
    VALIDATION_FAILED = "TSA-2002"
    CONFLICT = "TSA-2003"
    JOB_NOT_RUNNABLE = "TSA-3001"
    JOB_FAILED = "TSA-3002"
    EXPORT_FORBIDDEN = "TSA-3003"
    INTERNAL = "TSA-5000"


@dataclass
class AppError(Exception):
    code: str
    message: str = ""
    status_code: int = 400
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message:
            self.message = DEFAULT_MESSAGES.get(self.code, "请求处理失败")
        super().__init__(self.message)


DEFAULT_MESSAGES = {
    ErrorCode.UNAUTHORIZED: "未登录或登录已过期",
    ErrorCode.FORBIDDEN: "当前角色无权执行该操作",
    ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后再试",
    ErrorCode.QUOTA_EXHAUSTED: "今日对齐任务配额已用尽",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.VALIDATION_FAILED: "请求参数校验未通过",
    ErrorCode.CONFLICT: "资源状态冲突",
    ErrorCode.JOB_NOT_RUNNABLE: "任务当前状态不可执行",
    ErrorCode.JOB_FAILED: "对齐任务执行失败",
    ErrorCode.EXPORT_FORBIDDEN: "当前角色无导出权限",
    ErrorCode.INTERNAL: "服务内部错误",
}
