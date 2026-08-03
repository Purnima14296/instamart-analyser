"""Retry helper for connector network calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
    description: str = "operation",
) -> tuple[T, int]:
    """Execute fn with exponential backoff. Returns (result, retry_count)."""
    last_error: Exception | None = None
    retries = 0

    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), retries
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            retries += 1
            sleep_for = backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s failed (attempt %d/%d): %s. Retrying in %.1fs",
                description,
                attempt,
                max_attempts,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)

    raise RuntimeError(f"{description} failed after {max_attempts} attempts") from last_error
