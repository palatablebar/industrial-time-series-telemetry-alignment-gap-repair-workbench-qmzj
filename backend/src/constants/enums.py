"""Domain enums shared by API services and the Vue front-end constants/enums.ts."""
from enum import StrEnum


class Role(StrEnum):
    ENGINEER = "engineer"
    ANALYST = "analyst"
    VIEWER = "viewer"


class SourceProtocol(StrEnum):
    OPCUA = "opcua"
    DCS = "dcs"
    CSV = "csv"


class GridSize(StrEnum):
    S1 = "1"
    S5 = "5"
    S60 = "60"

    @classmethod
    def values(cls) -> list[int]:
        return [1, 5, 60]


class AggStrategy(StrEnum):
    MEAN = "mean"
    LAST = "last"
    LINEAR = "linear"


class FillStrategy(StrEnum):
    LOCF = "locf"
    LINEAR = "linear"
    SEASONAL_NAIVE = "seasonal_naive"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GapSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FailureReason(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    TIMESTAMP_DISORDER = "timestamp_disorder"
    NO_DATA = "no_data"
    INTERNAL_ERROR = "internal_error"
