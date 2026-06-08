"""Transparent technical diagnostics for the futures monitor."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .analyzers.directional_matrix import build_direction_matrix, month_from_day
from .domain.nanhua_boards import resolve_nanhua_board
from .skills import analyze_contract
from .trading_hours import session_info


MIN_AVG_VOLUME_20 = 1000
MIN_AVG_OI_20 = 1000


@dataclass
class PeriodFrames:
    day: pd.DataFrame
    week: pd.DataFrame


def prepare_kline(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["close"])
    if "datetime" in data:
        data["time"] = pd.to_datetime(data["datetime"], errors="coerce")
    return data.reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    data = prepare_kline(df)
    if len(data) == 0:
        return data

    for n in (5, 20, 60):
        data[f"ma{n}"] = data["close"].rolling(n).mean()

    prev_close = data["close"].shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["atr14"] = true_range.rolling(14).mean()
    data["range_pct"] = (data["high"] / data["low"] - 1).replace([np.inf, -np.inf], np.nan)
    data["return_pct"] = data["close"].pct_change()
    data["volume_rank_60"] = rolling_percentile(data["volume"], 60)
    data["oi_rank_60"] = rolling_percentile(data["open_oi"], 60) if "open_oi" in data else np.nan
    data["atr_rank_60"] = rolling_percentile(data["atr14"], 60)
    data["range_rank_60"] = rolling_percentile(data["range_pct"], 60)
    data["boll_width"] = (
        data["close"].rolling(20).std() * 4 / data["close"].rolling(20).mean()
    )
    data["boll_width_rank_120"] = rolling_percentile(data["boll_width"], 120)
    data["prev_high_20"] = data["high"].shift(1).rolling(20).max()
    data["prev_low_20"] = data["low"].shift(1).rolling(20).min()
    data["prev_high_60"] = data["high"].shift(1).rolling(60).max()
    data["prev_low_60"] = data["low"].shift(1).rolling(60).min()
    return data


def rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    def pct_rank(values: np.ndarray) -> float:
        clean = values[~np.isnan(values)]
        if len(clean) < max(5, window // 3):
            return np.nan
        return float((clean <= clean[-1]).sum() / len(clean))

    return series.rolling(window).apply(pct_rank, raw=True)


def diagnose_contract(
    meta: dict[str, Any],
    frames: PeriodFrames,
    quote: dict[str, Any],
    board_context: dict[str, Any] | None = None,
    chain_quotes: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    day = add_indicators(frames.day)
    week = add_indicators(frames.week)
    month = month_from_day(day)
    if len(day) < 70:
        return None

    last = day.iloc[-1]
    prev = day.iloc[-2] if len(day) >= 2 else last
    avg_volume_20 = safe_mean(day["volume"].tail(20))
    avg_oi_20 = safe_mean(day["open_oi"].tail(20)) if "open_oi" in day else np.nan
    if avg_volume_20 < MIN_AVG_VOLUME_20 or avg_oi_20 < MIN_AVG_OI_20:
        return None

    state = classify_state(last, prev)
    direction = direction_for_state(state)
    day_path = period_path(day)
    week_bias = weekly_bias(week)
    score = score_state(state, last, prev, day_path, week_bias)

    context = board_context or {}
    level = classify_level(state, last, day_path, week_bias, context)
    facts = build_facts(last, prev)
    evidence = build_evidence(state, last, prev, week_bias, context)
    to_confirm = build_confirmations(state, direction, last)
    invalidation = build_invalidations(state, direction, last)
    quote_for_specs = dict(quote)
    if clean_number(quote_for_specs.get("last_price")) is None:
        quote_for_specs["last_price"] = last.get("close")
    outputs = analyze_contract(
        periods={"day": day, "week": week},
        state=state,
        level=level,
        direction=direction,
        score=score,
        chain_quotes=chain_quotes,
        meta=meta,
        quote=quote_for_specs,
        include_external=bool(context.get("include_external_analyzers", context.get("include_external_skills", True))),
        macro_context=context.get("macro"),
        board_peers=context.get("board_peers"),
        boards_summary=context.get("boards_summary"),
    )

    return {
        **resolve_nanhua_board(meta.get("board")),
        "name": meta["name"],
        "symbol": meta["symbol"],
        "actual_symbol": quote.get("underlying_symbol") or quote.get("symbol") or meta["symbol"],
        "last_price": clean_number(quote.get("last_price")),
        "quote_time": quote.get("datetime"),
        "session": session_info(symbol=meta.get("symbol")),
        "state": state,
        "direction": direction,
        "level": level,
        "score": score,
        "facts": facts,
        "evidence": evidence,
        "to_confirm": to_confirm,
        "invalidation": invalidation,
        "metrics": {
            "close": clean_number(last.get("close")),
            "return_pct": clean_number(last.get("return_pct") * 100),
            "range_pct": clean_number(last.get("range_pct") * 100),
            "volume_rank_60": clean_number(last.get("volume_rank_60") * 100),
            "atr_rank_60": clean_number(last.get("atr_rank_60") * 100),
            "open_interest_change_pct": clean_number(
                (last.get("open_oi") / prev.get("open_oi") - 1) * 100
            )
            if prev.get("open_oi")
            else None,
            "ma20": clean_number(last.get("ma20")),
            "ma60": clean_number(last.get("ma60")),
            "prev_high_20": clean_number(last.get("prev_high_20")),
            "prev_low_20": clean_number(last.get("prev_low_20")),
            "prev_high_60": clean_number(last.get("prev_high_60")),
            "prev_low_60": clean_number(last.get("prev_low_60")),
            "volume_multiple": clean_number(quote_for_specs.get("volume_multiple")),
            "price_tick": clean_number(quote_for_specs.get("price_tick")),
            "tick_value": tick_value(quote_for_specs),
            "contract_value": contract_value(quote_for_specs),
            "estimated_margin": estimated_margin(quote_for_specs),
            "avg_daily_range_amount_5d": avg_daily_range_amount(day, quote_for_specs, 5),
        },
        "charts": {
            "day": chart_rows(day, 120),
            "week": chart_rows(week, 100),
        },
        "direction_matrix": build_direction_matrix(
            {"day": day, "week": week, "month": month}
        ),
        "analyzers": outputs["analyzers"],
        "skills": outputs["skills"],
    }


def classify_state(last: pd.Series, prev: pd.Series) -> str:
    close = last["close"]
    upper_shadow = last["high"] - max(last["open"], last["close"])
    lower_shadow = min(last["open"], last["close"]) - last["low"]
    body = abs(last["close"] - last["open"])
    high_vol = last.get("volume_rank_60", 0) >= 0.75
    uptrend = close > last.get("ma20", np.nan) > last.get("ma60", np.nan)
    downtrend = close < last.get("ma20", np.nan) < last.get("ma60", np.nan)

    if uptrend and high_vol and upper_shadow > max(body * 1.5, last.get("atr14", 0) * 0.35):
        return "趋势上行后的反转预警"
    if downtrend and high_vol and lower_shadow > max(body * 1.5, last.get("atr14", 0) * 0.35):
        return "趋势下行后的反转预警"
    if close > last.get("prev_high_20", np.inf) and high_vol:
        return "日线向上突破确认中"
    if close < last.get("prev_low_20", -np.inf) and high_vol:
        return "日线向下突破确认中"
    if uptrend:
        return "日线趋势上行"
    if downtrend:
        return "日线趋势下行"
    if max(last.get("atr_rank_60", 0), last.get("range_rank_60", 0)) >= 0.85:
        return "波动扩张但方向未确认"
    if last.get("boll_width_rank_120", 1) <= 0.2 and last.get("volume_rank_60", 1) <= 0.45:
        return "震荡收敛等待方向"
    return "中性无明确信号"


def score_state(state: str, last: pd.Series, prev: pd.Series, day_path: str, week: str) -> int:
    score = 35
    if "突破" in state:
        score += 25
    elif "趋势" in state:
        score += 18
    elif "波动扩张" in state:
        score += 16
    elif "反转预警" in state:
        score += 20
    elif "收敛" in state:
        score += 10

    score += int(nan_to_zero(last.get("volume_rank_60")) * 12)
    score += int(nan_to_zero(last.get("atr_rank_60")) * 8)
    oi_change = (last.get("open_oi") / prev.get("open_oi") - 1) if prev.get("open_oi") else 0
    if abs(oi_change) >= 0.02:
        score += 6
    if day_path in ("连续上行", "连续下行"):
        score += 4
    if ("上行" in state and week == "周线偏强") or ("下行" in state and week == "周线偏弱"):
        score += 5
    if state == "中性无明确信号":
        score = min(score, 45)
    return int(max(0, min(score, 100)))


def classify_level(state: str, last: pd.Series, day_path: str, week: str, context: dict[str, Any]) -> str:
    same_direction_count = context.get("same_direction_count", 0)
    volume_ok = nan_to_zero(last.get("volume_rank_60")) >= 0.75
    oi_ok = abs(context.get("oi_change_pct", 0) or 0) >= 1.5
    breakout_60 = last["close"] > last.get("prev_high_60", np.inf) or last["close"] < last.get("prev_low_60", -np.inf)
    if "突破" in state and breakout_60 and volume_ok and oi_ok and same_direction_count >= 3 and week != "周线逆向":
        return "大行情候选，仍需后续确认"
    if ("突破" in state or "趋势" in state) and volume_ok and day_path in ("连续上行", "连续下行"):
        return "中级行情候选"
    if state == "中性无明确信号":
        return "暂无行情级别"
    if "波动扩张" in state or "收敛" in state:
        return "小行情或变盘前状态"
    return "小行情，需观察能否扩展"


def build_facts(last: pd.Series, prev: pd.Series) -> str:
    ret = pct(last.get("return_pct"))
    rng = pct(last.get("range_pct"))
    vol_rank = pct_rank(last.get("volume_rank_60"))
    oi_change = pct(last.get("open_oi") / prev.get("open_oi") - 1) if prev.get("open_oi") else "不可用"
    return f"主连日线收盘价 {fmt(last.get('close'))}，当日涨跌幅 {ret}，振幅 {rng}；成交量处于近60日日线 {vol_rank}，持仓较前一交易日变化 {oi_change}。"


def build_evidence(
    state: str,
    last: pd.Series,
    prev: pd.Series,
    week: str,
    context: dict[str, Any],
) -> list[str]:
    items = []
    if "向上突破" in state:
        items.append(f"收盘价高于近20日高点 {fmt(last.get('prev_high_20'))}。")
    elif "向下突破" in state:
        items.append(f"收盘价低于近20日低点 {fmt(last.get('prev_low_20'))}。")
    elif "趋势上行" in state:
        items.append(f"收盘价位于MA20 {fmt(last.get('ma20'))} 和MA60 {fmt(last.get('ma60'))} 上方。")
    elif "趋势下行" in state:
        items.append(f"收盘价位于MA20 {fmt(last.get('ma20'))} 和MA60 {fmt(last.get('ma60'))} 下方。")
    elif "波动扩张" in state:
        items.append(f"ATR分位为 {pct_rank(last.get('atr_rank_60'))}，振幅分位为 {pct_rank(last.get('range_rank_60'))}。")
    elif "收敛" in state:
        items.append(f"布林带宽度处于近120日 {pct_rank(last.get('boll_width_rank_120'))}。")
    elif "反转预警" in state:
        items.append("趋势结构中出现放量长影线，说明原方向承接出现分歧。")

    items.append(f"成交量处于近60日 {pct_rank(last.get('volume_rank_60'))}。")
    if prev.get("open_oi"):
        items.append(f"持仓变化为 {pct(last.get('open_oi') / prev.get('open_oi') - 1)}。")
    items.append(f"周线背景：{week}。")
    if context.get("same_direction_count") is not None:
        items.append(f"同板块同方向品种数：{context.get('same_direction_count')}。")
    return items


def build_confirmations(state: str, direction: str, last: pd.Series) -> list[str]:
    if direction == "up":
        return [
            f"未来1-3个交易日收盘继续站在突破/均线关键位上方，参考位 {fmt(last.get('prev_high_20') or last.get('ma20'))}。",
            "回撤时成交量不明显放大，持仓不快速回落。",
            "日线结构继续保持高低点抬高。",
        ]
    if direction == "down":
        return [
            f"未来1-3个交易日收盘继续压在突破/均线关键位下方，参考位 {fmt(last.get('prev_low_20') or last.get('ma20'))}。",
            "反弹时成交量不明显放大，持仓不快速回落。",
            "日线结构继续保持高低点下移。",
        ]
    if "波动扩张" in state or "收敛" in state:
        return ["等待日线收盘突破近20日区间，并观察成交量与持仓是否同步。"]
    return ["目前缺少足够确认条件，优先观察是否出现放量突破或多周期共振。"]


def build_invalidations(state: str, direction: str, last: pd.Series) -> list[str]:
    if direction == "up":
        return [
            f"收盘跌回近20日突破位或MA20下方，参考位 {fmt(last.get('prev_high_20') or last.get('ma20'))}。",
            "放量上涨后持仓快速下降，说明可能只是减仓推动。",
        ]
    if direction == "down":
        return [
            f"收盘重新站回近20日突破位或MA20上方，参考位 {fmt(last.get('prev_low_20') or last.get('ma20'))}。",
            "放量下跌后持仓快速下降，说明可能只是减仓推动。",
        ]
    return ["若波动放大后价格回到原区间内部，且成交量回落，则按一日游处理。"]


def period_path(df: pd.DataFrame) -> str:
    data = add_indicators(df)
    if len(data) < 30:
        return "数据不足"
    tail = data.tail(12)
    close = tail["close"]
    ma20 = data["ma20"].tail(12)
    if close.iloc[-1] > close.iloc[0] and close.iloc[-1] > ma20.iloc[-1]:
        return "连续上行"
    if close.iloc[-1] < close.iloc[0] and close.iloc[-1] < ma20.iloc[-1]:
        return "连续下行"
    if (tail["high"].max() - tail["low"].min()) / tail["close"].iloc[-1] > 0.025:
        return "宽幅震荡"
    return "窄幅震荡"


def weekly_bias(df: pd.DataFrame) -> str:
    data = add_indicators(df)
    if len(data) < 30:
        return "周线数据不足"
    last = data.iloc[-1]
    if last["close"] > last.get("ma20", np.nan) > last.get("ma60", np.nan):
        return "周线偏强"
    if last["close"] < last.get("ma20", np.nan) < last.get("ma60", np.nan):
        return "周线偏弱"
    return "周线震荡"


def direction_for_state(state: str) -> str:
    if "上行" in state or "向上" in state:
        return "up"
    if "下行" in state or "向下" in state:
        return "down"
    return "neutral"


def board_context(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_board: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_board.setdefault(item["board"], []).append(item)

    result = {}
    for board, board_items in by_board.items():
        up = sum(1 for item in board_items if item.get("direction") == "up")
        down = sum(1 for item in board_items if item.get("direction") == "down")
        result[board] = {
            "count": len(board_items),
            "up": up,
            "down": down,
            "tone": "偏强" if up > down else "偏弱" if down > up else "分化",
        }
    return result


def safe_mean(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").mean()
    return 0.0 if pd.isna(value) else float(value)


def nan_to_zero(value: Any) -> float:
    try:
        if value is None or math.isnan(value):
            return 0.0
        return float(value)
    except TypeError:
        return 0.0


def clean_number(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def chart_rows(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = []
    data = df.tail(limit)
    for _, row in data.iterrows():
        time_value = row.get("time")
        if pd.isna(time_value):
            label = ""
        else:
            label = pd.Timestamp(time_value).strftime("%Y-%m-%d %H:%M")
        rows.append(
            {
                "time": label,
                "open": clean_number(row.get("open")),
                "high": clean_number(row.get("high")),
                "low": clean_number(row.get("low")),
                "close": clean_number(row.get("close")),
                "volume": clean_number(row.get("volume")),
                "ma20": clean_number(row.get("ma20")),
                "ma60": clean_number(row.get("ma60")),
            }
        )
    return [
        row
        for row in rows
        if row["open"] is not None
        and row["high"] is not None
        and row["low"] is not None
        and row["close"] is not None
    ]


def contract_value(quote: dict[str, Any]) -> float | None:
    explicit_value = clean_number(quote.get("contract_value"))
    if explicit_value is not None and explicit_value > 0:
        return explicit_value
    last_price = clean_number(quote.get("last_price"))
    multiplier = clean_number(quote.get("volume_multiple"))
    if last_price is None or multiplier is None:
        return None
    return clean_number(last_price * multiplier)


def tick_value(quote: dict[str, Any]) -> float | None:
    explicit_value = clean_number(quote.get("tick_value"))
    if explicit_value is not None and explicit_value > 0:
        return explicit_value
    price_tick = clean_number(quote.get("price_tick"))
    multiplier = clean_number(quote.get("volume_multiple"))
    if price_tick is None or multiplier is None:
        return None
    return clean_number(price_tick * multiplier)


def estimated_margin(quote: dict[str, Any]) -> float | None:
    explicit_margin = clean_number(quote.get("margin"))
    if explicit_margin is not None and explicit_margin > 1:
        return explicit_margin

    value = contract_value(quote)
    if value is None:
        return None

    rate = first_valid_number(
        quote,
        (
            "long_margin_rate",
            "short_margin_rate",
            "margin_rate",
            "long_margin_ratio",
            "short_margin_ratio",
            "margin_ratio",
            "margin",
        ),
    )
    if rate is None:
        return None
    if rate > 1:
        rate = rate / 100
    return clean_number(value * rate)


def avg_daily_range_amount(df: pd.DataFrame, quote: dict[str, Any], days: int) -> float | None:
    multiplier = clean_number(quote.get("volume_multiple"))
    if multiplier is None or len(df) == 0:
        return None
    ranges = (df["high"] - df["low"]).tail(days)
    avg_range = safe_mean(ranges)
    return clean_number(avg_range * multiplier)


def first_valid_number(data: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = clean_number(data.get(key))
        if value is not None and value > 0:
            return value
    return None


def fmt(value: Any) -> str:
    number = clean_number(value)
    if number is None:
        return "不可用"
    return f"{number:g}"


def pct(value: Any) -> str:
    number = clean_number(value)
    if number is None:
        return "不可用"
    return f"{number:.2f}%"


def pct_rank(value: Any) -> str:
    number = clean_number(value)
    if number is None:
        return "不可用"
    return f"{number:.1f}%分位"
