from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    name: str | None = Field(default=None, max_length=140)
    device_codes: list[str] = Field(min_length=1, max_length=20)
    window_start: str
    window_end: str
    grid_s: int = 5
    agg_strategy: str = "linear"
    fill_strategy: str = "linear"
    note: str = ""


class JobOut(BaseModel):
    id: int
    name: str
    device_codes: list[str]
    signal_codes: list[str]
    window_start: str
    window_end: str
    grid_s: int
    agg_strategy: str
    fill_strategy: str
    status: str
    error_reason: str
    note: str
    created_by_name: str | None = None
    run_id: int | None = None
    quality_score: float | None = None
    created_at: str

    model_config = {"from_attributes": True}


class JobList(BaseModel):
    items: list[JobOut]


class EstimateRequest(BaseModel):
    device_codes: list[str]
    window_start: str
    window_end: str
    grid_s: int = 5


class EstimateResponse(BaseModel):
    bucket_count: int
    point_count: int
    signal_count: int
    span_seconds: int
    grid_s: int
