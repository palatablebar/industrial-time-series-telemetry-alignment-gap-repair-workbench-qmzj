from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class RawTelemetry(Base):
    """One raw sample exported by a gateway (the alignment engine's input)."""

    __tablename__ = "raw_telemetry"
    __table_args__ = (UniqueConstraint("signal_id", "ts", name="uq_raw_signal_ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signal.id"), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"), nullable=False, index=True)
    ts: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0)
