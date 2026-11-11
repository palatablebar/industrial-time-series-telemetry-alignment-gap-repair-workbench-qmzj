"""Small helpers around local (Asia/Shanghai) timestamps and epoch floats."""
from datetime import datetime, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=8))


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0)


def to_epoch(dt: datetime) -> float:
    """Naive DB datetimes are local wall time; convert to epoch seconds."""
    return dt.replace(tzinfo=LOCAL_TZ).timestamp()


def from_epoch(value: float) -> datetime:
    return datetime.fromtimestamp(value, LOCAL_TZ).replace(tzinfo=None, microsecond=0)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse_iso(value: str) -> datetime:
    text = value.strip().replace("Z", "")
    if "T" in text:
        parsed = datetime.fromisoformat(text)
    else:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return parsed


def human_span(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{rest:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"
