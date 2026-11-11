from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class Signal(Base):
    __tablename__ = "signal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"), nullable=False, index=True)
    device_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    device_name: Mapped[str] = mapped_column(String(80), default="")
    measure_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tag_path: Mapped[str] = mapped_column(String(160), default="")
    unit: Mapped[str] = mapped_column(String(24), default="")
    sampling_interval_s: Mapped[int] = mapped_column(Integer, default=5)
    scale_min: Mapped[float] = mapped_column(Float, default=0.0)
    scale_max: Mapped[float] = mapped_column(Float, default=100.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source = relationship("DataSource", lazy="joined")
