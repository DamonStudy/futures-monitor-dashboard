"""Support, resistance, confirmation and invalidation levels."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .schema import signal, module_result, table
from .utils import clean_number, fmt_number, last_two, period_label


def analyze(periods: dict[str, pd.DataFrame]) -> dict[str, Any]:
    levels = []
    signals = []
    rows = []
    priority = 45

    for period, df in periods.items():
        last, _ = last_two(df)
        if last is None:
            continue
        close = clean_number(last.get("close"))
        if close is None:
            continue

        period_levels = _levels_for_period(period, last, close)
        levels.extend(period_levels)
        rows.extend(_rows_for_period(period_levels))

        nearest_support = _nearest(period_levels, close, "support")
        nearest_resistance = _nearest(period_levels, close, "resistance")
        if nearest_support:
            distance = (close / nearest_support["price"] - 1) * 100
            if 0 <= distance <= 1:
                priority = max(priority, 66)
                signals.append(
                    signal(
                        "接近支撑位",
                        f"{period_label(period)}收盘价距离{nearest_support['name']}约{distance:.2f}%，需要观察能否守住。",
                        period=period,
                        level="watch",
                        value=fmt_number(nearest_support["price"]),
                        threshold="距离 <=1%",
                    )
                )
        if nearest_resistance:
            distance = (nearest_resistance["price"] / close - 1) * 100
            if 0 <= distance <= 1:
                priority = max(priority, 66)
                signals.append(
                    signal(
                        "接近压力位",
                        f"{period_label(period)}收盘价距离{nearest_resistance['name']}约{distance:.2f}%，突破与否会影响后续强弱判断。",
                        period=period,
                        level="watch",
                        value=fmt_number(nearest_resistance["price"]),
                        threshold="距离 <=1%",
                    )
                )

    summary = "已生成关键支撑、压力、确认和失效位。" if levels else "暂无关键点位。"
    return module_result(
        "key_levels",
        "关键点位",
        summary,
        priority=priority,
        signals=signals,
        levels=levels,
        tables=[table("周期 × 关键点位", ["周期", "类型", "名称", "价格", "距离"], rows)],
    )


def _levels_for_period(period: str, row: pd.Series, close: float) -> list[dict[str, Any]]:
    candidates = [
        ("resistance", "近20周期高点", row.get("prev_high_20")),
        ("support", "近20周期低点", row.get("prev_low_20")),
        ("resistance", "近60周期高点", row.get("prev_high_60")),
        ("support", "近60周期低点", row.get("prev_low_60")),
        ("dynamic", "MA20", row.get("ma20")),
        ("dynamic", "MA60", row.get("ma60")),
    ]
    atr = clean_number(row.get("atr14"))
    if atr is not None:
        candidates.extend(
            [
                ("resistance", "收盘价+1ATR", close + atr),
                ("support", "收盘价-1ATR", close - atr),
            ]
        )

    result = []
    for kind, name, value in candidates:
        price = clean_number(value)
        if price is None or price <= 0:
            continue
        actual_kind = kind
        if kind == "dynamic":
            actual_kind = "support" if price <= close else "resistance"
        result.append(
            {
                "period": period,
                "period_label": period_label(period),
                "type": actual_kind,
                "name": name,
                "price": price,
                "distance_pct": clean_number((price / close - 1) * 100, 2),
            }
        )
    return result


def _nearest(levels: list[dict[str, Any]], close: float, kind: str) -> dict[str, Any] | None:
    same_kind = [level for level in levels if level["type"] == kind]
    if kind == "support":
        same_kind = [level for level in same_kind if level["price"] <= close]
        return max(same_kind, key=lambda item: item["price"], default=None)
    same_kind = [level for level in same_kind if level["price"] >= close]
    return min(same_kind, key=lambda item: item["price"], default=None)


def _rows_for_period(levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {"support": "支撑", "resistance": "压力"}
    return [
        {
            "周期": item["period_label"],
            "类型": labels.get(item["type"], item["type"]),
            "名称": item["name"],
            "价格": item["price"],
            "距离": f"{item['distance_pct']:.2f}%" if item["distance_pct"] is not None else "-",
        }
        for item in levels
    ]

