"""Price and volume diagnostics across periods."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .schema import signal, module_result, table
from .utils import clean_number, last_two, pct_text, pct_value, period_label, simple_path


def analyze(periods: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rows = []
    signals = []
    max_priority = 45

    for period, df in periods.items():
        last, prev = last_two(df)
        if last is None or prev is None:
            continue

        ret = pct_value(last.get("return_pct"))
        range_pct = pct_value(last.get("range_pct"))
        volume_rank = pct_value(last.get("volume_rank_60"))
        atr_rank = pct_value(last.get("atr_rank_60"))
        oi_change = None
        if prev.get("open_oi"):
            oi_change = pct_value(last.get("open_oi") / prev.get("open_oi") - 1)

        path = simple_path(df)
        rows.append(
            {
                "周期": period_label(period),
                "收盘": clean_number(last.get("close")),
                "涨跌幅": pct_text(ret),
                "振幅": pct_text(range_pct),
                "成交量": clean_number(last.get("volume"), 0),
                "成交量分位": pct_text(volume_rank),
                "持仓变化": pct_text(oi_change),
                "ATR分位": pct_text(atr_rank),
                "路径": path,
            }
        )

        label = period_label(period)
        if volume_rank is not None and volume_rank >= 75:
            max_priority = max(max_priority, 70)
            signals.append(
                signal(
                    "成交量进入高分位",
                    f"{label}成交量处于近60周期较高位置，当前价格动作更值得跟踪。",
                    period=period,
                    level="watch",
                    value=pct_text(volume_rank),
                    threshold=">=75%",
                )
            )
        if atr_rank is not None and atr_rank >= 85:
            max_priority = max(max_priority, 75)
            signals.append(
                signal(
                    "波动扩张",
                    f"{label}ATR处于高分位，说明波动率环境正在放大。",
                    period=period,
                    level="watch",
                    value=pct_text(atr_rank),
                    threshold=">=85%",
                )
            )
        if oi_change is not None and abs(oi_change) >= 2:
            max_priority = max(max_priority, 65)
            signals.append(
                signal(
                    "持仓明显变化",
                    f"{label}持仓变化超过2%，需要结合价格方向判断增仓推动还是减仓波动。",
                    period=period,
                    level="info",
                    value=pct_text(oi_change),
                    threshold="abs >=2%",
                )
            )

    summary = "暂无足够量价数据。"
    if rows:
        lead = rows[0]
        summary = f"{lead['周期']}涨跌幅{lead['涨跌幅']}，成交量分位{lead['成交量分位']}，路径为{lead['路径']}。"

    return module_result(
        "price_volume",
        "量价分析",
        summary,
        priority=max_priority,
        signals=signals,
        tables=[
            table(
                "周期 × 量价维度",
                ["周期", "收盘", "涨跌幅", "振幅", "成交量", "成交量分位", "持仓变化", "ATR分位", "路径"],
                rows,
            )
        ],
    )

