from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class GapEvent(Base):
    __tablename__ = "gap_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("alignment_run.id"), nullable=False, index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signal.id"), nullable=False, index=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_s: Mapped[float] = mapped_column(Float, default=0.0)
    bucket_length: Mapped[int] = mapped_column(Integer, default=0)
    fill_strategy: Mapped[str] = mapped_column(String(24), default="linear")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(12), default="low", index=True)
    annotated: Mapped[bool] = mapped_column(Boolean, default=False)
    annotation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    signal = relationship("Signal", lazy="joined")
