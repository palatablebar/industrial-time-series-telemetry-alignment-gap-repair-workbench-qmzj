from pydantic import BaseModel


class ReportSummary(BaseModel):
    customer: str
    generated_at: str
    run_count: int
    completed_runs: int
    average_quality: float
    best_coverage: float
    total_gaps: int
    formula: str
    quality_trend: list[dict]
    drift_table: list[dict]
    gap_severity: list[dict]
    recent_runs: list[dict]
    quota: dict
