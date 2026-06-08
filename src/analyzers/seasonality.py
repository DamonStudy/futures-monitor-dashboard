"""Seasonal patterns — playbook notes + multi-year calendar overlay (THS-style)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..research.registry import get_board_playbook, get_product_playbook
from .schema import signal, module_result, table
from .utils import clean_number, pct_text


MIN_YEARS = 3
MONTH_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]


def analyze(*, meta: dict[str, Any], day: pd.DataFrame | None = None) -> dict[str, Any]:
    notes = qualitative_notes(meta)
    seasonal = build_seasonal_model(day)

    if not notes and seasonal.get("status") != "ok":
        return module_result(
            "seasonality",
            "季节性",
            "暂无季节性要点，且历史日线不足以生成季节图。",
            status="unavailable",
            priority=38,
            notes=["可在 Playbook 补充 seasonal_notes；刷新需拉取约 5 年主连日线。"],
        )

    signals: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    priority = 42

    if notes:
        tables.append(table("季节性要点", ["类型", "描述"], [_qual_row(item) for item in notes[:8]]))
        for item in notes[:3]:
            signals.append(signal(f"{item['type']}季节特征", item["text"], level="info"))

    quant_summary = ""
    if seasonal.get("status") == "ok":
        priority = max(priority, seasonal.get("priority", 50))
        signals.extend(seasonal.get("signals", []))
        tables.append(seasonal["month_table"])
        charts.append(seasonal["chart"])
        quant_summary = seasonal.get("summary", "")

    qual_summary = "；".join(item["text"] for item in notes[:2]) if notes else ""
    summary = "。".join(part for part in [qual_summary, quant_summary] if part)

    return module_result(
        "seasonality",
        "季节性",
        summary or "季节性分析已生成。",
        priority=priority,
        signals=signals[:8],
        tables=tables,
        charts=charts,
        notes=[
            "季节图按主连日线收盘价，将各年价格叠在 1–12 月日历轴上（参考同花顺季节图）。",
            "月度涨跌概率按历年同月收益率统计；定性要点来自 Playbook。",
        ],
    )


def qualitative_notes(meta: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    symbol = meta.get("symbol")
    board = meta.get("board")

    product = get_product_playbook(symbol)
    if product:
        for text in product.get("seasonal_notes") or []:
            if text:
                rows.append({"type": product.get("name") or "品种", "text": str(text).strip()})

    board_playbook = get_board_playbook(board)
    if board_playbook:
        for text in board_playbook.get("seasonal_notes") or []:
            text = str(text).strip()
            if not text or any(item["text"] == text for item in rows):
                continue
            rows.append({"type": board_playbook.get("name") or "板块", "text": text})

    return rows


def build_seasonal_model(day: pd.DataFrame | None) -> dict[str, Any]:
    frame = prepare_day_frame(day)
    if frame is None or len(frame) < 200:
        return {"status": "unavailable", "summary": "历史日线不足，无法生成季节图。"}

    anchor = pd.Timestamp(frame.iloc[-1]["date"])
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["doy"] = frame["date"].dt.dayofyear

    years = sorted(int(y) for y in frame["year"].unique())
    if len(years) < MIN_YEARS:
        return {"status": "unavailable", "summary": f"有效年份不足 {MIN_YEARS} 个。"}

    series = [_year_series(frame, year, anchor.year) for year in years]
    series = [item for item in series if item and item.get("points")]
    if len(series) < MIN_YEARS:
        return {"status": "unavailable", "summary": "各年交易日样本不足。"}

    month_stats = _month_statistics(frame, anchor)
    focus_month = int(anchor.month)
    focus = next((row for row in month_stats if row["month"] == focus_month), None)
    interpretation = _month_interpretation(focus_month, focus)

    current_series = next((item for item in series if item["year"] == anchor.year), None)
    signals = []
    if interpretation:
        signals.append(
            signal(
                f"{focus_month}月季节统计",
                interpretation,
                level="info",
                value=pct_text(focus.get("avg_return_pct")) if focus else None,
                threshold=f"上涨概率 {focus.get('up_prob_pct'):.1f}%" if focus else None,
            )
        )

    return {
        "status": "ok",
        "priority": 56 if focus and abs(focus.get("avg_return_pct") or 0) >= 1 else 48,
        "summary": interpretation or "已生成多年季节图与月度统计。",
        "signals": signals,
        "interpretation": interpretation,
        "chart": {
            "type": "seasonal",
            "title": "季节图",
            "focus_month": focus_month,
            "focus_doy": int(anchor.dayofyear),
            "interpretation": interpretation,
            "series": series,
            "month_stats": month_stats,
        },
        "month_table": table(
            "历年分月涨跌统计",
            ["月份", "样本年数", "月均涨跌", "上涨概率", "下跌概率"],
            [
                {
                    "月份": row["label"] + (" ◀" if row["month"] == focus_month else ""),
                    "样本年数": row["samples"],
                    "月均涨跌": pct_text(row["avg_return_pct"]),
                    "上涨概率": f"{row['up_prob_pct']:.1f}%",
                    "下跌概率": f"{row['down_prob_pct']:.1f}%",
                }
                for row in month_stats
            ],
        ),
    }


def prepare_day_frame(day: pd.DataFrame | None) -> pd.DataFrame | None:
    if day is None or day.empty or "close" not in day:
        return None
    frame = day.copy()
    if "time" in frame:
        frame["date"] = pd.to_datetime(frame["time"], errors="coerce")
    elif "datetime" in frame:
        frame["date"] = pd.to_datetime(frame["datetime"], errors="coerce")
    else:
        return None
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values("date")
    return frame.reset_index(drop=True) if not frame.empty else None


def _year_series(frame: pd.DataFrame, year: int, current_year: int) -> dict[str, Any] | None:
    segment = frame[frame["year"] == year]
    if len(segment) < 30:
        return None
    points = []
    for _, row in segment.iterrows():
        date = pd.Timestamp(row["date"])
        close = clean_number(row["close"])
        if close is None:
            continue
        points.append(
            {
                "doy": int(date.dayofyear),
                "md": date.strftime("%m-%d"),
                "month": int(date.month),
                "close": close,
            }
        )
    if not points:
        return None
    last_point = points[-1]
    return {
        "year": year,
        "in_progress": year == current_year,
        "last_close": last_point["close"],
        "last_md": last_point["md"],
        "points": points,
    }


def _month_statistics(frame: pd.DataFrame, anchor: pd.Timestamp) -> list[dict[str, Any]]:
    """Month-over-month return per year, then aggregate by calendar month."""
    frame = frame.copy()
    frame["ym"] = frame["date"].dt.to_period("M")
    monthly = (
        frame.groupby("ym", as_index=False)
        .agg(close=("close", "last"), date=("date", "last"))
        .sort_values("date")
    )
    monthly["return_pct"] = monthly["close"].pct_change() * 100
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month

    current_year = int(anchor.year)
    current_month = int(anchor.month)

    stats: list[dict[str, Any]] = []
    for month in range(1, 13):
        rows = monthly[
            (monthly["month"] == month)
            & monthly["return_pct"].notna()
            & ~(
                (monthly["year"] == current_year)
                & (monthly["month"] > current_month)
            )
        ]
        returns = [float(v) for v in rows["return_pct"] if pd.notna(v)]
        if not returns:
            stats.append(
                {
                    "month": month,
                    "label": MONTH_LABELS[month - 1],
                    "samples": 0,
                    "avg_return_pct": None,
                    "up_prob_pct": None,
                    "down_prob_pct": None,
                }
            )
            continue
        up = sum(1 for value in returns if value > 0)
        down = sum(1 for value in returns if value < 0)
        total = len(returns)
        stats.append(
            {
                "month": month,
                "label": MONTH_LABELS[month - 1],
                "samples": total,
                "avg_return_pct": clean_number(float(np.mean(returns)), 2),
                "up_prob_pct": clean_number(up / total * 100, 1),
                "down_prob_pct": clean_number(down / total * 100, 1),
            }
        )
    return stats


def _month_interpretation(month: int, focus: dict[str, Any] | None) -> str:
    if not focus or not focus.get("samples"):
        return f"历年{month}月样本不足，暂无法统计季节概率。"
    avg = float(focus["avg_return_pct"] or 0)
    up_prob = float(focus["up_prob_pct"] or 0)
    down_prob = float(focus["down_prob_pct"] or 0)
    direction = "上涨" if avg > 0.05 else "下跌" if avg < -0.05 else "震荡"
    dominant_prob = up_prob if up_prob >= down_prob else down_prob
    dominant_dir = "上涨" if up_prob >= down_prob else "下跌"
    return (
        f"历年{month}月平均{direction}{abs(avg):.2f}%，"
        f"{dominant_dir}概率{dominant_prob:.1f}%（样本{focus['samples']}年）。"
        f"涨跌幅按主连日线月末收盘价环比计算。"
    )


def _qual_row(item: dict[str, str]) -> dict[str, str]:
    return {"类型": item.get("type") or "要点", "描述": item.get("text") or "-"}
