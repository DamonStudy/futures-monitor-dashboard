"""Futures-only term structure and calendar spread diagnostics."""

from __future__ import annotations

import re
from typing import Any

from .schema import signal, module_result, table
from .utils import clean_number
from ..sources.market.term_chain import chain_is_ready, fetch_chain_quotes

__all__ = ["analyze", "chain_is_ready", "fetch_chain_quotes"]


def analyze(chain_quotes: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = [_quote_row(item) for item in (chain_quotes or [])]
    rows = [row for row in rows if row["last_price"] is not None]
    rows.sort(key=lambda item: (item["month_sort"], item["symbol"]))

    if len(rows) < 2:
        subscribed = len(chain_quotes or [])
        notes = [
            "基于同品种多个期货合约的最新价计算期限结构与跨期价差，不使用现货基差。",
            f"本次订阅 {subscribed} 个合约，有效报价 {len(rows)} 个。",
        ]
        if subscribed < 2:
            notes.append("未查到足够上市合约，请确认天勤连接正常后点「刷新数据」。")
        else:
            notes.append("合约已查到但缺少有效价格，可在交易时段刷新或稍后重试。")
        return module_result(
            "term_structure",
            "期限结构",
            "暂无足够合约链报价，先不判断期限结构。",
            status="unavailable",
            notes=notes,
        )

    near = rows[0]
    far = rows[-1]
    main = max(rows, key=lambda item: (item.get("open_interest") or 0, item.get("volume") or 0))
    far_near = _spread(far, near)
    main_near = _spread(main, near)
    far_main = _spread(far, main)
    adjacent = [_spread(rows[i + 1], rows[i]) for i in range(len(rows) - 1)]
    shape = _classify_shape(adjacent, far_near)

    signals = [
        signal(
            shape,
            _interpret_shape(shape),
            level="info" if shape in ("平坦结构", "远月升水", "近月升水") else "watch",
            value=f"{far_near['spread_pct']:.2f}%" if far_near["spread_pct"] is not None else None,
        )
    ]
    if abs(far_near.get("spread_pct") or 0) >= 2:
        signals.append(
            signal(
                "近远月价差较大",
                "近远月价差超过2%，说明合约链内部定价差异较明显，适合纳入跨期观察。",
                level="watch",
                value=f"{far_near['spread_pct']:.2f}%",
                threshold="abs >=2%",
            )
        )

    spread_rows = [
        _spread_row("远月-近月", far_near),
        _spread_row("主力-近月", main_near),
        _spread_row("远月-主力", far_main),
    ]

    summary = f"{shape}，远月-近月价差{far_near['spread']:+g}，价差率{far_near['spread_pct']:.2f}%。"
    return module_result(
        "term_structure",
        "期限结构",
        summary,
        priority=72 if "扭曲" in shape else 58,
        signals=signals,
        tables=[
            table("合约链报价", ["合约", "月份", "价格", "成交量", "持仓"], [_curve_row(row) for row in rows]),
            table("跨期价差", ["价差", "近端", "远端", "点差", "价差率"], spread_rows),
        ],
        charts=[{"type": "line", "title": "期限结构曲线", "points": [_curve_row(row) for row in rows]}],
        notes=["仅比较期货合约链内部价差，不包含现货升贴水。"],
    )


def _quote_row(item: dict[str, Any]) -> dict[str, Any]:
    quote = item.get("quote", item)
    symbol = item.get("symbol") or _value(quote, "instrument_id") or _value(quote, "underlying_symbol")
    month = _contract_month(symbol)
    return {
        "symbol": symbol,
        "month": month or "-",
        "month_sort": _month_sort(month),
        "last_price": _extract_price(quote),
        "volume": clean_number(_value(quote, "volume"), 0),
        "open_interest": clean_number(_value(quote, "open_interest") or _value(quote, "open_oi"), 0),
    }


def _extract_price(quote: Any) -> float | None:
    for key in ("last_price", "close", "pre_close"):
        price = clean_number(_value(quote, key))
        if price is not None and price > 0:
            return price
    bid = clean_number(_value(quote, "bid_price1"))
    ask = clean_number(_value(quote, "ask_price1"))
    if bid and ask and bid > 0 and ask > 0:
        return clean_number((bid + ask) / 2)
    return bid if bid and bid > 0 else ask if ask and ask > 0 else None


def _value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    if hasattr(obj, "get"):
        value = obj.get(key)
        if value is not None:
            return value
    return getattr(obj, key, None)


def _contract_month(symbol: Any) -> str | None:
    if not symbol:
        return None
    match = re.search(r"([A-Za-z]+)([0-9]{3,4})$", str(symbol).split(".")[-1])
    return match.group(2) if match else None


def _month_sort(month: str | None) -> int:
    if not month:
        return 999999
    text = str(month)
    if len(text) == 3:
        text = "2" + text
    return int(text)


def _spread(far: dict[str, Any], near: dict[str, Any]) -> dict[str, Any]:
    spread = clean_number(far["last_price"] - near["last_price"])
    spread_pct = clean_number(spread / near["last_price"] * 100, 2) if near["last_price"] else None
    return {"near": near, "far": far, "spread": spread, "spread_pct": spread_pct}


def _classify_shape(adjacent: list[dict[str, Any]], far_near: dict[str, Any]) -> str:
    pct = far_near.get("spread_pct")
    if pct is None:
        return "结构不可判定"
    signs = [item["spread"] for item in adjacent if item.get("spread") is not None]
    if signs and any(sign > 0 for sign in signs) and any(sign < 0 for sign in signs):
        return "局部扭曲"
    if abs(pct) < 0.2:
        return "平坦结构"
    return "远月升水" if pct > 0 else "近月升水"


def _interpret_shape(shape: str) -> str:
    return {
        "远月升水": "远端合约价格高于近端，说明期货合约链内部远期定价更强。",
        "近月升水": "近端合约价格高于远端，说明期货合约链内部近端定价更强。",
        "平坦结构": "近远月价格差异较小，合约链暂未给出明显期限方向。",
        "局部扭曲": "相邻合约价差方向不一致，可能存在换月、流动性或局部预期差异。",
    }.get(shape, "合约链数据不足以形成明确结构判断。")


def _curve_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "合约": row["symbol"],
        "月份": row["month"],
        "价格": row["last_price"],
        "成交量": row["volume"],
        "持仓": row["open_interest"],
    }


def _spread_row(name: str, spread: dict[str, Any]) -> dict[str, Any]:
    return {
        "价差": name,
        "近端": spread["near"]["symbol"],
        "远端": spread["far"]["symbol"],
        "点差": spread["spread"],
        "价差率": f"{spread['spread_pct']:.2f}%" if spread["spread_pct"] is not None else "-",
    }

