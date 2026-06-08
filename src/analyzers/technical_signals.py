"""TA-Lib backed technical signal diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .schema import signal, module_result, table
from .utils import clean_number, last_two, pct_text, period_label, series_values

try:
    import talib
except Exception:  # pragma: no cover - depends on local native installation
    talib = None


def analyze(periods: dict[str, pd.DataFrame]) -> dict[str, Any]:
    if talib is None:
        return module_result(
            "technical_signals",
            "技术指标",
            "TA-Lib 不可用，技术指标模块暂未运行。",
            status="unavailable",
            notes=["安装 TA-Lib 后可启用 MACD、RSI、KDJ、ADX、布林带等信号。"],
        )

    rows = []
    signals = []
    priority = 45

    for period, df in periods.items():
        close = series_values(df, "close")
        high = series_values(df, "high")
        low = series_values(df, "low")
        if len(close) < 35 or len(high) != len(close) or len(low) != len(close):
            continue

        macd, macd_signal, macd_hist = talib.MACD(close)
        rsi = talib.RSI(close, timeperiod=14)
        slowk, slowd = talib.STOCH(high, low, close)
        upper, _, lower = talib.BBANDS(close, timeperiod=20)
        adx = talib.ADX(high, low, close, timeperiod=14)
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=14)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
        atr = talib.ATR(high, low, close, timeperiod=14)

        last, _ = last_two(df)
        atr_rank = None if last is None else clean_number((last.get("atr_rank_60") or 0) * 100)
        rows.append(
            {
                "周期": period_label(period),
                "MACD柱": clean_number(_last(macd_hist)),
                "RSI14": clean_number(_last(rsi), 2),
                "K": clean_number(_last(slowk), 2),
                "D": clean_number(_last(slowd), 2),
                "ADX": clean_number(_last(adx), 2),
                "ATR14": clean_number(_last(atr)),
                "ATR分位": pct_text(atr_rank),
                "布林位置": _boll_position(_last(close), _last(upper), _last(lower)),
            }
        )

        label = period_label(period)
        if _cross_up(macd, macd_signal):
            priority = max(priority, 78)
            signals.append(signal("MACD金叉", f"{label}DIF上穿DEA，动能边际转强。", period=period, level="watch"))
        if _cross_down(macd, macd_signal):
            priority = max(priority, 78)
            signals.append(signal("MACD死叉", f"{label}DIF下穿DEA，动能边际转弱。", period=period, level="watch"))
        if _last(rsi) >= 70:
            priority = max(priority, 65)
            signals.append(signal("RSI偏热", f"{label}RSI进入高位区，追涨性价比下降。", period=period, value=clean_number(_last(rsi), 2), threshold=">=70"))
        if _last(rsi) <= 30:
            priority = max(priority, 65)
            signals.append(signal("RSI偏冷", f"{label}RSI进入低位区，关注修复或延续下跌的分歧。", period=period, value=clean_number(_last(rsi), 2), threshold="<=30"))
        if _cross_up(slowk, slowd) and _last(slowk) <= 35:
            priority = max(priority, 70)
            signals.append(signal("KDJ低位金叉", f"{label}K线上穿D线且位置偏低，短线修复概率上升。", period=period, level="watch"))
        if _cross_down(slowk, slowd) and _last(slowk) >= 65:
            priority = max(priority, 70)
            signals.append(signal("KDJ高位死叉", f"{label}K线下穿D线且位置偏高，短线回落风险上升。", period=period, level="watch"))
        if _last(adx) >= 25:
            direction = "偏多" if _last(plus_di) > _last(minus_di) else "偏空"
            priority = max(priority, 68)
            signals.append(
                signal(
                    "ADX趋势强度提升",
                    f"{label}ADX超过25，趋势强度提升，DI结构{direction}。",
                    period=period,
                    value=clean_number(_last(adx), 2),
                    threshold=">=25",
                )
            )
        if _last(close) > _last(upper):
            priority = max(priority, 72)
            signals.append(signal("突破布林上轨", f"{label}收盘越过布林上轨，可能是强趋势或短线过热。", period=period, level="watch"))
        if _last(close) < _last(lower):
            priority = max(priority, 72)
            signals.append(signal("跌破布林下轨", f"{label}收盘跌破布林下轨，可能是弱趋势或短线超跌。", period=period, level="watch"))

    summary = "暂无明显技术指标阈值信号。" if not signals else f"发现{len(signals)}个技术指标信号。"
    return module_result(
        "technical_signals",
        "技术指标",
        summary,
        priority=priority,
        signals=signals,
        tables=[table("周期 × 技术指标", ["周期", "MACD柱", "RSI14", "K", "D", "ADX", "ATR14", "ATR分位", "布林位置"], rows)],
    )


def _last(values: np.ndarray) -> float:
    if len(values) == 0:
        return float("nan")
    return float(values[-1])


def _prev(values: np.ndarray) -> float:
    if len(values) < 2:
        return float("nan")
    return float(values[-2])


def _cross_up(left: np.ndarray, right: np.ndarray) -> bool:
    return _prev(left) <= _prev(right) and _last(left) > _last(right)


def _cross_down(left: np.ndarray, right: np.ndarray) -> bool:
    return _prev(left) >= _prev(right) and _last(left) < _last(right)


def _boll_position(close: float, upper: float, lower: float) -> str:
    if not all(np.isfinite(v) for v in (close, upper, lower)):
        return "-"
    if close > upper:
        return "上轨外"
    if close < lower:
        return "下轨外"
    span = max(upper - lower, 1e-9)
    pos = (close - lower) / span
    if pos >= 0.8:
        return "靠近上轨"
    if pos <= 0.2:
        return "靠近下轨"
    return "中轨附近"
