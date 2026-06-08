"""Macro data and economic calendar for commodity monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .calendar import fetch_economic_calendar
from .snapshot import fetch_macro_snapshot


def build_macro_context(*, calendar_days: int = 7) -> dict[str, Any]:
    """Fetch macro snapshot + calendar once per refresh batch."""
    errors: list[str] = []
    snapshot = _safe(fetch_macro_snapshot, errors) or {}
    calendar = _safe(lambda: fetch_economic_calendar(days=calendar_days), errors) or {}

    status = "ok"
    if errors and (snapshot or calendar.get("events")):
        status = "partial"
    elif errors:
        status = "unavailable"

    return {
        "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "snapshot": snapshot,
        "calendar": calendar,
        "errors": errors,
    }


def _safe(fn, errors: list[str]):
    try:
        return fn()
    except Exception as exc:
        errors.append(str(exc))
        return None
