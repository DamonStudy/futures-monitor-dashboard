"""Macro indicator snapshot — rates, FX, and key macro releases."""

from __future__ import annotations

from typing import Any

from ..sources.macro.drivers import fetch_macro_drivers


RELEASE_SPECS = [
    ("macro_usa_non_farm", "美国非农就业", "万人", "美国"),
    ("macro_usa_cpi_monthly", "美国CPI月率", "%", "美国"),
    ("macro_usa_core_cpi_monthly", "美国核心CPI月率", "%", "美国"),
    ("macro_usa_pmi", "美国ISM制造业PMI", "指数", "美国"),
    ("macro_china_cpi_monthly", "中国CPI月率", "%", "中国"),
    ("macro_china_ppi_yearly", "中国PPI年率", "%", "中国"),
    ("macro_china_pmi_yearly", "中国官方制造业PMI", "指数", "中国"),
]


def fetch_macro_snapshot() -> dict[str, Any]:
    drivers = fetch_macro_drivers()
    releases = _fetch_latest_releases()
    return {
        "drivers": drivers,
        "releases": releases,
    }


def _fetch_latest_releases() -> list[dict[str, Any]]:
    import akshare as ak

    rows: list[dict[str, Any]] = []
    for func_name, title, unit, region in RELEASE_SPECS:
        if not hasattr(ak, func_name):
            continue
        try:
            df = getattr(ak, func_name)()
        except Exception:
            continue
        if df is None or df.empty:
            continue
        latest = _latest_published_row(df)
        if latest is None:
            continue
        previous = _previous_published_row(df, latest)
        actual = _clean(latest.get("今值"))
        forecast = _clean(latest.get("预测值"))
        prior = _clean(latest.get("前值") if latest.get("前值") is not None else previous.get("今值") if previous is not None else None)
        rows.append(
            {
                "id": func_name,
                "title": title,
                "region": region,
                "date": str(latest.get("日期") or ""),
                "actual": actual,
                "forecast": forecast,
                "previous": prior,
                "unit": unit,
                "pending": actual is None,
                "beat": _release_beat(actual, forecast),
            }
        )
    return rows


def _latest_published_row(df: Any) -> Any | None:
    for idx in range(len(df) - 1, -1, -1):
        row = df.iloc[idx]
        if _clean(row.get("今值")) is not None:
            return row
    return df.iloc[-1] if len(df) else None


def _previous_published_row(df: Any, latest: Any) -> Any | None:
    latest_idx = latest.name if hasattr(latest, "name") else None
    if latest_idx is not None:
        for idx in range(latest_idx - 1, -1, -1):
            row = df.iloc[idx]
            if _clean(row.get("今值")) is not None:
                return row
    for idx in range(len(df) - 2, -1, -1):
        row = df.iloc[idx]
        if _clean(row.get("今值")) is not None and row is not latest:
            return row
    return None


def _release_beat(actual: float | None, forecast: float | None) -> str | None:
    if actual is None or forecast is None:
        return None
    if actual > forecast:
        return "above"
    if actual < forecast:
        return "below"
    return "inline"


def _clean(value: Any) -> float | None:
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
