"""Small numeric helpers used by data analyzers."""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd


PERIOD_LABELS = {"day": "日线", "week": "周线"}
SIGNAL_PERIODS = ("day", "week")


def last_two(df: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    data = df.dropna(subset=["close"]) if "close" in df else df
    if len(data) == 0:
        return None, None
    last = data.iloc[-1]
    prev = data.iloc[-2] if len(data) >= 2 else last
    return last, prev


def clean_number(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
        if not math.isfinite(number):
            return None
        return round(number, digits)
    except (TypeError, ValueError):
        return None


def pct_value(value: Any) -> float | None:
    number = clean_number(value)
    return clean_number(number * 100) if number is not None else None


def pct_text(value: Any, digits: int = 2) -> str:
    number = clean_number(value, digits)
    return "-" if number is None else f"{number:.{digits}f}%"


def fmt_number(value: Any, digits: int = 2) -> str:
    number = clean_number(value, digits)
    if number is None:
        return "-"
    return f"{number:g}"


def safe_ratio(numerator: Any, denominator: Any) -> float | None:
    top = clean_number(numerator)
    bottom = clean_number(denominator)
    if top is None or bottom in (None, 0):
        return None
    return clean_number(top / bottom)


def series_values(df: pd.DataFrame, key: str) -> np.ndarray:
    if key not in df:
        return np.array([], dtype=float)
    return pd.to_numeric(df[key], errors="coerce").to_numpy(dtype=float)


def period_label(period: str) -> str:
    return PERIOD_LABELS.get(period, PERIOD_LABELS["day"])


def signal_periods(periods: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {key: df for key, df in periods.items() if key in SIGNAL_PERIODS}


def simple_path(df: pd.DataFrame) -> str:
    if len(df) < 20 or "close" not in df:
        return "数据不足"
    tail = df.tail(12)
    close = pd.to_numeric(tail["close"], errors="coerce")
    ma20 = pd.to_numeric(df.get("ma20"), errors="coerce").tail(12)
    if close.iloc[-1] > close.iloc[0] and close.iloc[-1] > ma20.iloc[-1]:
        return "连续上行"
    if close.iloc[-1] < close.iloc[0] and close.iloc[-1] < ma20.iloc[-1]:
        return "连续下行"
    width = (tail["high"].max() - tail["low"].min()) / max(abs(close.iloc[-1]), 1)
    return "宽幅震荡" if width > 0.025 else "窄幅震荡"


from ..symbol_parse import parse_product_symbol


def contract_month(symbol: str | None) -> str | None:
    if not symbol:
        return None
    match = re.search(r"([A-Za-z]+)([0-9]{3,4})$", str(symbol).split(".")[-1])
    if not match:
        return None
    return match.group(2)

