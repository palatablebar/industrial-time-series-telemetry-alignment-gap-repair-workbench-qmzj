from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class AlignmentJob(Base):
    __tablename__ = "alignment_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    device_codes: Mapped[list] = mapped_column(JSON, default=list)
    signal_codes: Mapped[list] = mapped_column(JSON, default=list)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    grid_s: Mapped[int] = mapped_column(Integer, nullable=False)
    agg_strategy: Mapped[str] = mapped_column(String(16), nullable=False)
    fill_strategy: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    error_reason: Mapped[str] = mapped_column(String(40), default="")
    params_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
