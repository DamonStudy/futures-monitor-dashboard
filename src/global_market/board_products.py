"""Build Nanhua board x product ranking matrix for the global dashboard."""

from __future__ import annotations

from typing import Any

from ..domain.nanhua_constituents import (
    COMPOSITE_NANHUA_CODES,
    LEAF_NANHUA_CODES,
    board_product_matrix_invalid,
    resolve_nanhua_index_for_item,
)
from ..sources.market.nanhua_indices import NANHUA_BOARD_INDICES

EXCLUDED_BOARDS = {"金融", "航运"}


def build_board_product_matrix(
    items: list[dict[str, Any]] | None,
    nanhua_indices: list[dict[str, Any]] | None = None,
    *,
    preview_limit: int = 10,
) -> dict[str, Any]:
    """Rank monitored contracts by 5-day return within each exclusive Nanhua leaf index."""
    if not items:
        return {"rows": [], "preview_limit": preview_limit, "status": "empty"}

    index_meta = {
        str(row.get("index_code") or row.get("id", "").replace(".NH", "")): row
        for row in (nanhua_indices or [])
        if row.get("group") != "总指数"
    }

    by_code: dict[str, list[dict[str, Any]]] = {code: [] for code in LEAF_NANHUA_CODES}
    for item in items:
        board = item.get("board") or "未分类"
        if board in EXCLUDED_BOARDS:
            continue
        change_5d = product_change_5d(item)
        if change_5d is None:
            continue
        code = resolve_nanhua_index_for_item(item)
        if not code or code not in by_code:
            continue
        by_code[code].append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "change_5d": change_5d,
                "direction": item.get("direction"),
                "last_price": item.get("last_price"),
            }
        )

    rows: list[dict[str, Any]] = []
    for ts_code, name, group in NANHUA_BOARD_INDICES:
        if group == "总指数":
            continue
        code = ts_code.replace(".NH", "")
        if code in COMPOSITE_NANHUA_CODES:
            continue
        products = list(by_code.get(code, []))
        products.sort(key=lambda row: row.get("change_5d") or -999, reverse=True)
        index_row = index_meta.get(code) or {}
        rows.append(
            {
                "id": ts_code,
                "code": code,
                "name": name,
                "group": group,
                "index_change_5d": (index_row.get("changes") or {}).get("5d"),
                "product_count": len(products),
                "products": products,
                "preview": products[:preview_limit],
                "hidden_count": max(0, len(products) - preview_limit),
            }
        )

    return {
        "rows": rows,
        "preview_limit": preview_limit,
        "status": "ok" if any(row["product_count"] for row in rows) else "empty",
    }


def product_change_5d(item: dict[str, Any]) -> float | None:
    day = (item.get("charts") or {}).get("day") or []
    if len(day) <= 5:
        return None
    latest = day[-1].get("close")
    base = day[-1 - 5].get("close")
    if latest is None or base in (None, 0):
        return None
    try:
        return round((float(latest) / float(base) - 1) * 100, 4)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


__all__ = [
    "build_board_product_matrix",
    "board_product_matrix_invalid",
    "product_change_5d",
]
