"""Economic calendar — when macro data releases happen."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

SCHEDULE_DIR = Path(__file__).resolve().parent / "schedules"

KEYWORDS = (
    "非农",
    "非农业",
    "就业",
    "CPI",
    "PCE",
    "通胀",
    "物价",
    "GDP",
    "PMI",
    "零售",
    "FOMC",
    "美联储",
    "联储",
    "议息",
    "利率",
    "鲍威尔",
    "Powell",
    "MLF",
    "LPR",
    "社融",
    "信贷",
    "制造业",
    "工业产出",
)

REGIONS = {"美国", "中国", "欧元区", "欧洲"}


def fetch_economic_calendar(*, days: int = 7, min_importance: int = 2) -> dict[str, Any]:
    import akshare as ak

    today = date.today()
    events: list[dict[str, Any]] = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        day_str = day.strftime("%Y%m%d")
        try:
            df = ak.macro_info_ws(date=day_str)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            event = _normalize_ws_event(row, day)
            if not event:
                continue
            if event["importance"] < min_importance:
                continue
            if event["region"] not in REGIONS and not _keyword_hit(event["title"]):
                continue
            if not _keyword_hit(event["title"]) and event["importance"] < 3:
                continue
            events.append(event)

    events.extend(_load_fomc_events(today, days))
    events = _dedupe_events(events)
    events.sort(key=lambda item: item["datetime"])

    now = datetime.now()
    upcoming = [event for event in events if event["datetime"] >= now - timedelta(hours=1)]
    next_event = upcoming[0] if upcoming else None
    risk_48h = any(event["datetime"] <= now + timedelta(hours=48) for event in upcoming if event["importance"] >= 2)

    return {
        "days": days,
        "events": _serialize_events(events[:40]),
        "upcoming": _serialize_events(upcoming[:20]),
        "next_event": _serialize_event(next_event),
        "high_importance_count": sum(1 for event in upcoming if event["importance"] >= 3),
        "risk_window_48h": risk_48h,
    }


def _serialize_event(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event:
        return None
    row = dict(event)
    dt = row.get("datetime")
    if isinstance(dt, datetime):
        row["datetime"] = dt.isoformat(sep=" ")
    return row


def _serialize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_serialize_event(event) or {} for event in events]


def _normalize_ws_event(row: pd.Series, day: date) -> dict[str, Any] | None:
    title = str(row.get("事件") or "").strip()
    if not title:
        return None
    region = str(row.get("地区") or "").strip()
    time_text = str(row.get("时间") or "").strip()
    try:
        dt = pd.to_datetime(time_text).to_pydatetime()
    except Exception:
        dt = datetime.combine(day, datetime.min.time())
    importance = _to_int(row.get("重要性"), default=1)
    return {
        "datetime": dt.replace(tzinfo=None),
        "date": dt.date().isoformat(),
        "time": dt.strftime("%H:%M"),
        "region": region,
        "title": title,
        "importance": importance,
        "forecast": _text(row.get("预期")),
        "previous": _text(row.get("前值")),
        "actual": _text(row.get("今值")),
        "source": "华尔街见闻",
    }


def _load_fomc_events(today: date, days: int) -> list[dict[str, Any]]:
    path = SCHEDULE_DIR / "fomc.yaml"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    end = today + timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for item in data.get("meetings") or []:
        if not isinstance(item, dict):
            continue
        meeting_date = item.get("date")
        if not meeting_date:
            continue
        try:
            day = date.fromisoformat(str(meeting_date))
        except ValueError:
            continue
        if day < today or day > end:
            continue
        dt = datetime.combine(day, datetime.min.time().replace(hour=3, minute=0))
        rows.append(
            {
                "datetime": dt,
                "date": day.isoformat(),
                "time": "03:00",
                "region": "美国",
                "title": item.get("label") or "FOMC 利率决议",
                "importance": 3,
                "forecast": None,
                "previous": None,
                "actual": None,
                "source": "FOMC 日程",
            }
        )
    return rows


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for event in events:
        key = f"{event['date']}|{event['time']}|{event['title']}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(event)
    return rows


def _keyword_hit(text: str) -> bool:
    upper = text.upper()
    return any(keyword.upper() in upper for keyword in KEYWORDS)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text or None


def _to_int(value: Any, *, default: int) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default
