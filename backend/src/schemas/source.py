from pydantic import BaseModel, Field


class SignalOut(BaseModel):
    id: int
    code: str
    source_id: int
    device_code: str
    device_name: str
    measure_name: str
    tag_path: str
    unit: str
    sampling_interval_s: int
    is_active: bool

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: int
    code: str
    name: str
    protocol: str
    sample_interval_s: int
    timezone: str
    drift_hint_ms: int
    status: str
    workshop: str
    description: str
    last_capture_at: str | None = None

    model_config = {"from_attributes": True}


class SourceDetail(BaseModel):
    source: SourceOut
    signals: list[SignalOut]
    raw_point_count: int
    signal_count: int


class SourceList(BaseModel):
    items: list[SourceOut]


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    status: str | None = None
    drift_hint_ms: int | None = None
    description: str | None = None


class SourceCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    protocol: str
    sample_interval_s: int
    workshop: str = ""
    description: str = ""


class SignalCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    source_id: int
    device_code: str
    device_name: str = ""
    measure_name: str
    tag_path: str = ""
    unit: str = ""
    sampling_interval_s: int = 5
