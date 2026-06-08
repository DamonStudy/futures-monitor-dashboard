"""Three-state direction matrix for a single futures contract."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


PERIODS = [
    {"key": "day", "label": "日线"},
    {"key": "week", "label": "周线"},
    {"key": "month", "label": "月线"},
]

DIMENSIONS = [
    {"key": "trend", "label": "趋势"},
    {"key": "momentum", "label": "动量"},
    {"key": "price_volume", "label": "量价"},
    {"key": "pattern", "label": "形态"},
    {"key": "fundamental", "label": "基本面"},
    {"key": "news", "label": "资讯"},
]

BIAS_LABELS = {"long": "多", "short": "空", "neutral": "中立"}


def build_direction_matrix(periods: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Build a period x dimension matrix with long/short/neutral cells."""
    prepared = {key: add_matrix_indicators(df) for key, df in periods.items()}
    cells = []

    for period in PERIODS:
        key = period["key"]
        df = prepared.get(key, pd.DataFrame())
        for dimension in DIMENSIONS:
            cell = classify_cell(df, key, period["label"], dimension["key"], dimension["label"])
            cells.append(cell)

    return {
        "periods": PERIODS,
        "dimensions": DIMENSIONS,
        "states": [
            {"key": "long", "label": "多"},
            {"key": "short", "label": "空"},
            {"key": "neutral", "label": "中立"},
        ],
        "cells": cells,
        "summary": summarize_matrix(cells),
    }


def month_from_day(day: pd.DataFrame) -> pd.DataFrame:
    data = day.copy()
    if data.empty:
        return pd.DataFrame()
    if "time" in data:
        data["time"] = pd.to_datetime(data["time"], errors="coerce")
    elif "datetime" in data:
        data["time"] = pd.to_datetime(data["datetime"], errors="coerce")
    else:
        return pd.DataFrame()
    data = data.dropna(subset=["time", "open", "high", "low", "close"])
    if data.empty:
        return pd.DataFrame()

    data = data.set_index("time").sort_index()
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    if "open_oi" in data:
        agg["open_oi"] = "last"

    try:
        monthly = data.resample("ME").agg(agg)
    except ValueError:
        monthly = data.resample("M").agg(agg)
    monthly = monthly.dropna(subset=["open", "high", "low", "close"])
    monthly["datetime"] = monthly.index
    return monthly.reset_index(drop=True)


def classify_cell(
    df: pd.DataFrame,
    period_key: str,
    period_label: str,
    dimension_key: str,
    dimension_label: str,
) -> dict[str, Any]:
    if dimension_key == "fundamental":
        return cell(
            period_key,
            period_label,
            dimension_key,
            dimension_label,
            "neutral",
            "第一版暂未接入按周期拆分的基本面字段。",
            ["库存、利润、基差、期限结构等产业数据后续可接入这一行。"],
        )
    if dimension_key == "news":
        return cell(
            period_key,
            period_label,
            dimension_key,
            dimension_label,
            "neutral",
            "第一版暂未接入热点资讯与新闻情绪。",
            ["后续可把资讯热度、政策事件、产业新闻映射成多/空/中立。"],
        )
    if len(df) < min_rows(period_key):
        return cell(
            period_key,
            period_label,
            dimension_key,
            dimension_label,
            "neutral",
            "可用K线不足，暂不判断方向。",
            [f"{period_label}至少需要{min_rows(period_key)}根有效K线。"],
        )

    if dimension_key == "trend":
        return trend_cell(df, period_key, period_label, dimension_key, dimension_label)
    if dimension_key == "momentum":
        return momentum_cell(df, period_key, period_label, dimension_key, dimension_label)
    if dimension_key == "price_volume":
        return price_volume_cell(df, period_key, period_label, dimension_key, dimension_label)
    if dimension_key == "pattern":
        return pattern_cell(df, period_key, period_label, dimension_key, dimension_label)

    return cell(period_key, period_label, dimension_key, dimension_label, "neutral", "暂无规则。", [])


def trend_cell(df: pd.DataFrame, period_key: str, period_label: str, dimension_key: str, dimension_label: str) -> dict[str, Any]:
    last = df.iloc[-1]
    close = last.get("close")
    ma20 = last.get("ma20")
    ma60 = last.get("ma60")
    slope20 = last.get("ma20_slope")

    reasons = [f"收盘 {fmt(close)}，MA20 {fmt(ma20)}，MA60 {fmt(ma60)}。"]
    if finite(close, ma20, ma60) and close > ma20 > ma60:
        reasons.append("价格位于MA20与MA60上方，均线呈多头排列。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "均线结构偏多。", reasons)
    if finite(close, ma20, ma60) and close < ma20 < ma60:
        reasons.append("价格位于MA20与MA60下方，均线呈空头排列。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "均线结构偏空。", reasons)
    if finite(close, ma20, slope20) and close > ma20 and slope20 > 0:
        reasons.append("价格站上MA20，且MA20斜率向上。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "短中期趋势偏多。", reasons)
    if finite(close, ma20, slope20) and close < ma20 and slope20 < 0:
        reasons.append("价格跌破MA20，且MA20斜率向下。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "短中期趋势偏空。", reasons)
    return cell(period_key, period_label, dimension_key, dimension_label, "neutral", "趋势结构未形成单边排列。", reasons)


def momentum_cell(df: pd.DataFrame, period_key: str, period_label: str, dimension_key: str, dimension_label: str) -> dict[str, Any]:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    hist = last.get("macd_hist")
    prev_hist = prev.get("macd_hist")
    rsi = last.get("rsi14")
    recent = last.get("recent_return")
    reasons = [
        f"MACD柱 {fmt(hist)}，RSI14 {fmt(rsi)}，近5根收益 {pct(recent)}。",
    ]
    if finite(hist, prev_hist, rsi) and hist > 0 and hist >= prev_hist and rsi >= 52:
        reasons.append("MACD柱在零轴上方且边际扩张，RSI处于偏强区。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "动量偏多。", reasons)
    if finite(hist, prev_hist, rsi) and hist < 0 and hist <= prev_hist and rsi <= 48:
        reasons.append("MACD柱在零轴下方且边际走弱，RSI处于偏弱区。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "动量偏空。", reasons)
    if finite(recent) and recent > 0.015:
        reasons.append("近5根K线累计涨幅较明显。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "短期动量偏多。", reasons)
    if finite(recent) and recent < -0.015:
        reasons.append("近5根K线累计跌幅较明显。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "短期动量偏空。", reasons)
    return cell(period_key, period_label, dimension_key, dimension_label, "neutral", "动量没有明显单边倾向。", reasons)


def price_volume_cell(df: pd.DataFrame, period_key: str, period_label: str, dimension_key: str, dimension_label: str) -> dict[str, Any]:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    ret = last.get("return_pct")
    volume_rank = last.get("volume_rank_60")
    oi_change = None
    if "open_oi" in df and prev.get("open_oi"):
        oi_change = last.get("open_oi") / prev.get("open_oi") - 1

    reasons = [
        f"涨跌幅 {pct(ret)}，成交量分位 {pct_rank(volume_rank)}，持仓变化 {pct(oi_change)}。",
    ]
    high_volume = finite(volume_rank) and volume_rank >= 0.6
    oi_support_long = oi_change is None or oi_change >= -0.01
    oi_support_short = oi_change is None or oi_change <= 0.01
    if finite(ret) and ret > 0 and high_volume and oi_support_long:
        reasons.append("上涨伴随成交活跃，持仓未明显拖累。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "量价偏多。", reasons)
    if finite(ret) and ret < 0 and high_volume and oi_support_short:
        reasons.append("下跌伴随成交活跃，持仓未明显拖累。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "量价偏空。", reasons)
    if finite(ret, volume_rank) and abs(ret) < 0.003 and volume_rank < 0.5:
        reasons.append("价格波动有限且成交不活跃。")
    else:
        reasons.append("价格方向与成交/持仓确认度不足。")
    return cell(period_key, period_label, dimension_key, dimension_label, "neutral", "量价暂未给出明确方向。", reasons)


def pattern_cell(df: pd.DataFrame, period_key: str, period_label: str, dimension_key: str, dimension_label: str) -> dict[str, Any]:
    last = df.iloc[-1]
    close = last.get("close")
    high20 = last.get("prev_high_20")
    low20 = last.get("prev_low_20")
    open_price = last.get("open")
    high = last.get("high")
    low = last.get("low")
    body = abs(close - open_price) if finite(close, open_price) else np.nan
    upper_shadow = high - max(open_price, close) if finite(high, open_price, close) else np.nan
    lower_shadow = min(open_price, close) - low if finite(low, open_price, close) else np.nan

    reasons = [f"近20周期高点 {fmt(high20)}，近20周期低点 {fmt(low20)}。"]
    if finite(close, high20) and close > high20:
        reasons.append("收盘突破前20周期高点。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "形态向上突破。", reasons)
    if finite(close, low20) and close < low20:
        reasons.append("收盘跌破前20周期低点。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "形态向下破位。", reasons)
    if finite(body, lower_shadow) and lower_shadow > max(body * 1.6, 1e-9):
        reasons.append("出现相对较长下影线，说明低位承接增强。")
        return cell(period_key, period_label, dimension_key, dimension_label, "long", "K线形态偏多。", reasons)
    if finite(body, upper_shadow) and upper_shadow > max(body * 1.6, 1e-9):
        reasons.append("出现相对较长上影线，说明高位抛压增强。")
        return cell(period_key, period_label, dimension_key, dimension_label, "short", "K线形态偏空。", reasons)
    reasons.append("未出现突破、破位或显著长影线。")
    return cell(period_key, period_label, dimension_key, dimension_label, "neutral", "形态维度中立。", reasons)


def add_matrix_indicators(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if data.empty or "close" not in data:
        return pd.DataFrame()
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=["close"]).reset_index(drop=True)
    if data.empty:
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    for n in (5, 20, 60):
        if f"ma{n}" not in data:
            data[f"ma{n}"] = close.rolling(n).mean()
    data["ma20_slope"] = data["ma20"] - data["ma20"].shift(5)
    data["return_pct"] = close.pct_change()
    data["recent_return"] = close / close.shift(5) - 1
    if "volume" in data and "volume_rank_60" not in data:
        data["volume_rank_60"] = rolling_percentile(pd.to_numeric(data["volume"], errors="coerce"), 60)
    elif "volume_rank_60" not in data:
        data["volume_rank_60"] = np.nan
    data["prev_high_20"] = pd.to_numeric(data["high"], errors="coerce").shift(1).rolling(20).max() if "high" in data else np.nan
    data["prev_low_20"] = pd.to_numeric(data["low"], errors="coerce").shift(1).rolling(20).min() if "low" in data else np.nan
    data["ema12"] = close.ewm(span=12, adjust=False).mean()
    data["ema26"] = close.ewm(span=26, adjust=False).mean()
    data["macd_diff"] = data["ema12"] - data["ema26"]
    data["macd_dea"] = data["macd_diff"].ewm(span=9, adjust=False).mean()
    data["macd_hist"] = data["macd_diff"] - data["macd_dea"]
    data["rsi14"] = rsi(close, 14)
    return data


def rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    def pct_rank(values: np.ndarray) -> float:
        clean = values[~np.isnan(values)]
        if len(clean) < max(5, window // 3):
            return np.nan
        return float((clean <= clean[-1]).sum() / len(clean))

    return series.rolling(window).apply(pct_rank, raw=True)


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def summarize_matrix(cells: list[dict[str, Any]]) -> dict[str, Any]:
    effective = [cell for cell in cells if cell["dimension_key"] not in {"fundamental", "news"}]
    long_count = sum(1 for cell in effective if cell["bias"] == "long")
    short_count = sum(1 for cell in effective if cell["bias"] == "short")
    neutral_count = sum(1 for cell in effective if cell["bias"] == "neutral")
    if long_count > short_count:
        bias = "long"
        text = f"可计算维度中多头格子 {long_count} 个，空头格子 {short_count} 个，整体偏多。"
    elif short_count > long_count:
        bias = "short"
        text = f"可计算维度中空头格子 {short_count} 个，多头格子 {long_count} 个，整体偏空。"
    else:
        bias = "neutral"
        text = f"可计算维度中多空格子均衡，中立格子 {neutral_count} 个，整体偏中性。"
    return {"bias": bias, "label": BIAS_LABELS[bias], "text": text}


def cell(
    period_key: str,
    period_label: str,
    dimension_key: str,
    dimension_label: str,
    bias: str,
    summary: str,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "period": period_key,
        "period_label": period_label,
        "dimension_key": dimension_key,
        "dimension": dimension_label,
        "bias": bias,
        "label": BIAS_LABELS[bias],
        "summary": summary,
        "reasons": reasons,
    }


def min_rows(period_key: str) -> int:
    if period_key == "month":
        return 8
    if period_key == "week":
        return 25
    return 35


def finite(*values: Any) -> bool:
    try:
        return all(value is not None and np.isfinite(float(value)) for value in values)
    except (TypeError, ValueError):
        return False


def fmt(value: Any) -> str:
    if not finite(value):
        return "不可用"
    return f"{float(value):g}"


def pct(value: Any) -> str:
    if not finite(value):
        return "不可用"
    return f"{float(value) * 100:.2f}%"


def pct_rank(value: Any) -> str:
    if not finite(value):
        return "不可用"
    return f"{float(value) * 100:.1f}%分位"
