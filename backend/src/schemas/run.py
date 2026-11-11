from pydantic import BaseModel


class DriftItem(BaseModel):
    source_id: int
    source_code: str
    drift_ms: float
    confidence: float
    is_anchor: bool = False
    is_estimated: bool = True
    correction_ms: float = 0.0
    evidence: list[dict] = []


class SeriesItem(BaseModel):
    signal_index: int
    signal_code: str
    device_code: str
    measure_name: str
    unit: str
    source_code: str
    source_codes: list[str] = []
    member_signal_codes: list[str] = []
    bucket_count: int
    observed_count: int
    coverage: float
    start_ts: float
    values: list[float | None]
    observed: list[bool]
    gap_filled: list[bool] = []
    provenance: list[str] = []
    contributors: list[list[str]] = []


class GapOut(BaseModel):
    id: int
    signal_code: str
    device_code: str
    measure_name: str
    start_ts: str
    end_ts: str
    duration_s: float
    bucket_length: int
    fill_strategy: str
    confidence: float
    severity: str
    annotated: bool
    annotation: str


class RunOut(BaseModel):
    id: int
    job_id: int
    job_name: str
    status: str
    started_at: str | None
    finished_at: str | None
    duration_ms: int
    coverage_pct: float
    drift_ms: float
    drift_confidence: float
    anomaly_rate: float
    quality_score: float
    gap_count: int
    gap_total_s: float
    point_count: int
    bucket_count: int
    failure_reason: str
    created_by_name: str | None = None


class RunDetail(RunOut):
    t0: str
    grid_s: int
    window_start: str
    window_end: str
    agg_strategy: str
    fill_strategy: str
    drift: list[DriftItem]
    corrections: list[dict] = []
    overlaps: list[dict] = []
    series: list[SeriesItem]
    gaps: list[GapOut]
    components: dict
    signal_coverage: list[dict]


class RunList(BaseModel):
    items: list[RunOut]
