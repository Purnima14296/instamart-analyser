"""Date helpers for review ingestion windows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DEFAULT_LOOKBACK_DAYS = 180  # 6 months


def review_cutoff(days: int = DEFAULT_LOOKBACK_DAYS) -> datetime:
    """Return UTC datetime for the oldest review to include."""
    return datetime.now(timezone.utc) - timedelta(days=days)


def parse_review_datetime(value: datetime | str | None) -> datetime | None:
    """Normalize review timestamps to UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_within_lookback(dt: datetime | None, days: int = DEFAULT_LOOKBACK_DAYS) -> bool:
    """Return True if dt is within the lookback window (or unknown)."""
    if dt is None:
        return True
    return dt >= review_cutoff(days)
