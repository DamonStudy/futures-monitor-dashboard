"""Fetch futures term-structure chain quotes from TqSdk."""

from __future__ import annotations

import re
from typing import Any

from ...symbol_parse import parse_product_symbol


def _clean_number(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        if number != number:
            return None
        return round(number, digits)
    except (TypeError, ValueError):
        return None


def count_priced_contracts(chain_quotes: list[dict[str, Any]] | None) -> int:
    rows = [_quote_row(item) for item in (chain_quotes or [])]
    return sum(1 for row in rows if row["last_price"] is not None)


def chain_is_ready(chain_quotes: list[dict[str, Any]] | None, min_contracts: int = 2) -> bool:
    return count_priced_contracts(chain_quotes) >= min_contracts


def fetch_chain_quotes(
    api: Any,
    meta: dict[str, Any],
    max_contracts: int = 8,
    main_quote: Any | None = None,
) -> list[dict[str, Any]]:
    exchange_id, product_id = _resolve_product(meta.get("symbol"), main_quote)
    if not product_id:
        return []

    symbols = _query_future_symbols(api, exchange_id, product_id)
    symbols = symbols[:max_contracts]
    if not symbols:
        return []
    quotes = api.get_quote_list(symbols)
    return [{"symbol": symbol, "quote": quote} for symbol, quote in zip(symbols, quotes)]


def _resolve_product(symbol: str | None, main_quote: Any | None = None) -> tuple[str | None, str | None]:
    exchange_id, product_id = parse_product_symbol(symbol)
    if main_quote is not None:
        underlying = _value(main_quote, "underlying_symbol") or _value(main_quote, "instrument_id")
        ex2, pid2 = _parse_instrument_product(underlying)
        exchange_id = exchange_id or ex2
        product_id = pid2 or product_id
    return exchange_id, product_id


def _parse_instrument_product(instrument_id: Any) -> tuple[str | None, str | None]:
    if not instrument_id:
        return None, None
    text = str(instrument_id)
    if "." not in text:
        return None, None
    exchange_id, tail = text.split(".", 1)
    match = re.match(r"([A-Za-z_]+)", tail)
    return exchange_id, match.group(1) if match else None


def _query_future_symbols(api: Any, exchange_id: str | None, product_id: str) -> list[str]:
    product_candidates = list(dict.fromkeys([product_id, product_id.upper(), product_id.lower()]))
    best: list[str] = []

    for pid in product_candidates:
        query_sets = []
        if exchange_id:
            query_sets.append({"ins_class": "FUTURE", "exchange_id": exchange_id, "product_id": pid, "expired": False})
        query_sets.append({"ins_class": "FUTURE", "product_id": pid, "expired": False})

        for params in query_sets:
            try:
                symbols = list(api.query_quotes(**params))
            except Exception:
                symbols = []
            futures = [symbol for symbol in symbols if _contract_month(symbol)]
            if len(futures) > len(best):
                best = futures

    best.sort(key=lambda symbol: (_month_sort(_contract_month(symbol)), symbol))
    return best


def _quote_row(item: dict[str, Any]) -> dict[str, Any]:
    quote = item.get("quote", item)
    symbol = item.get("symbol") or _value(quote, "instrument_id") or _value(quote, "underlying_symbol")
    month = _contract_month(symbol)
    return {
        "symbol": symbol,
        "month": month or "-",
        "month_sort": _month_sort(month),
        "last_price": _extract_price(quote),
        "volume": _clean_number(_value(quote, "volume"), 0),
        "open_interest": _clean_number(_value(quote, "open_interest") or _value(quote, "open_oi"), 0),
    }


def _extract_price(quote: Any) -> float | None:
    for key in ("last_price", "close", "pre_close"):
        price = _clean_number(_value(quote, key))
        if price is not None and price > 0:
            return price
    bid = _clean_number(_value(quote, "bid_price1"))
    ask = _clean_number(_value(quote, "ask_price1"))
    if bid and ask and bid > 0 and ask > 0:
        return _clean_number((bid + ask) / 2)
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
