from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class AlignmentRun(Base):
    __tablename__ = "alignment_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("alignment_job.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    drift_ms: Mapped[float] = mapped_column(Float, default=0.0)
    drift_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    anomaly_rate: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    gap_count: Mapped[int] = mapped_column(Integer, default=0)
    gap_total_s: Mapped[float] = mapped_column(Float, default=0.0)
    point_count: Mapped[int] = mapped_column(Integer, default=0)
    bucket_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str] = mapped_column(String(40), default="")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)

    job = relationship("AlignmentJob", lazy="joined")
