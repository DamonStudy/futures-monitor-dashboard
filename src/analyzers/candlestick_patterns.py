"""Candlestick pattern diagnostics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .schema import signal, module_result, table
from .utils import clean_number, last_two, period_label, series_values

try:
    import talib
except Exception:  # pragma: no cover - depends on local native installation
    talib = None


PATTERNS = {
    "CDLDOJI": ("十字星", "多空分歧加大，后续方向需要结合放量和关键位确认。"),
    "CDLENGULFING": ("吞没形态", "实体吞没前一根K线，可能暗示短线力量切换。"),
    "CDLHAMMER": ("锤头线", "下影线较长，低位时更偏向承接增强。"),
    "CDLSHOOTINGSTAR": ("射击之星", "上影线较长，高位时更偏向上方抛压增强。"),
    "CDLHANGINGMAN": ("上吊线", "上涨后出现长下影小实体，可能提示趋势分歧。"),
    "CDLHARAMI": ("孕线", "波动收窄到前一根实体内部，短线可能进入选择方向。"),
    "CDLPIERCING": ("刺透形态", "下跌后出现较强反包，可能提示修复。"),
    "CDLDARKCLOUDCOVER": ("乌云盖顶", "上涨后出现较强反包，可能提示回落。"),
    "CDLMORNINGSTAR": ("早晨之星", "多日组合转强信号，底部附近更有效。"),
    "CDLEVENINGSTAR": ("黄昏之星", "多日组合转弱信号，高位附近更有效。"),
}


def analyze(periods: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rows = []
    signals = []
    priority = 40

    for period, df in periods.items():
        last, _ = last_two(df)
        if last is None:
            continue
        manual = _manual_pattern(last)
        rows.append(
            {
                "周期": period_label(period),
                "基础形态": manual["name"],
                "实体占比": manual["body_ratio"],
                "上影占比": manual["upper_ratio"],
                "下影占比": manual["lower_ratio"],
            }
        )
        if manual["signal"]:
            priority = max(priority, manual["priority"])
            signals.append(manual["signal"] | {"period": period})

        if talib is None:
            continue
        open_ = series_values(df, "open")
        high = series_values(df, "high")
        low = series_values(df, "low")
        close = series_values(df, "close")
        if min(len(open_), len(high), len(low), len(close)) < 10:
            continue

        for func_name, (label, interpretation) in PATTERNS.items():
            values = getattr(talib, func_name)(open_, high, low, close)
            score = int(values[-1]) if len(values) else 0
            if score == 0:
                continue
            direction = "偏多" if score > 0 else "偏空"
            priority = max(priority, 72)
            signals.append(
                signal(
                    f"{label}（{direction}）",
                    f"{period_label(period)}出现{label}，{interpretation}",
                    period=period,
                    level="watch",
                    value=score,
                )
            )

    summary = "暂无显著K线形态。" if not signals else f"识别到{len(signals)}个形态提示。"
    status = "ok" if talib is not None else "partial"
    notes = [] if talib is not None else ["TA-Lib 不可用时仅运行手工长影线/十字星规则。"]
    return module_result(
        "candlestick_patterns",
        "形态学",
        summary,
        priority=priority,
        status=status,
        signals=signals,
        tables=[table("周期 × K线形态", ["周期", "基础形态", "实体占比", "上影占比", "下影占比"], rows)],
        notes=notes,
    )


def _manual_pattern(row: pd.Series) -> dict[str, Any]:
    open_ = clean_number(row.get("open"))
    high = clean_number(row.get("high"))
    low = clean_number(row.get("low"))
    close = clean_number(row.get("close"))
    if None in (open_, high, low, close):
        return {"name": "数据不足", "body_ratio": None, "upper_ratio": None, "lower_ratio": None, "signal": None, "priority": 40}

    full_range = max(high - low, 1e-9)
    body = abs(close - open_)
    upper = high - max(open_, close)
    lower = min(open_, close) - low
    body_ratio = clean_number(body / full_range * 100, 2)
    upper_ratio = clean_number(upper / full_range * 100, 2)
    lower_ratio = clean_number(lower / full_range * 100, 2)

    if body / full_range <= 0.12:
        return {
            "name": "十字星/小实体",
            "body_ratio": body_ratio,
            "upper_ratio": upper_ratio,
            "lower_ratio": lower_ratio,
            "priority": 62,
            "signal": signal("十字星/小实体", "实体占振幅比例很低，多空暂时均衡，后续需要等待方向确认。", level="info"),
        }
    if upper > body * 1.8 and upper / full_range >= 0.45:
        return {
            "name": "长上影",
            "body_ratio": body_ratio,
            "upper_ratio": upper_ratio,
            "lower_ratio": lower_ratio,
            "priority": 68,
            "signal": signal("长上影", "上影线明显偏长，说明上方抛压或冲高回落压力增强。", level="watch"),
        }
    if lower > body * 1.8 and lower / full_range >= 0.45:
        return {
            "name": "长下影",
            "body_ratio": body_ratio,
            "upper_ratio": upper_ratio,
            "lower_ratio": lower_ratio,
            "priority": 68,
            "signal": signal("长下影", "下影线明显偏长，说明下方承接或探底回升力量增强。", level="watch"),
        }
    return {"name": "普通K线", "body_ratio": body_ratio, "upper_ratio": upper_ratio, "lower_ratio": lower_ratio, "signal": None, "priority": 40}
