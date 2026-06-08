"""Trading session helpers — resolve session from static product catalog."""

from __future__ import annotations

from typing import Any

from .product_sessions import get_product_session
from .symbol_parse import product_id_from_symbol


def session_for_symbol(symbol: str | None) -> dict[str, Any]:
    product = product_id_from_symbol(symbol)
    profile = get_product_session(product)
    if profile:
        return profile
    return {
        "has_night": False,
        "night_session": "",
        "day_session": "",
        "label": "夜盘未知",
        "source": "unknown",
    }


def session_info(_quote: dict[str, Any] | None = None, *, symbol: str | None = None) -> dict[str, Any]:
    """Backward-compatible entry; session is static product metadata, not quote-driven."""
    return session_for_symbol(symbol)


def hydrate_item_session(item: dict[str, Any]) -> None:
    item["session"] = session_for_symbol(item.get("symbol"))
