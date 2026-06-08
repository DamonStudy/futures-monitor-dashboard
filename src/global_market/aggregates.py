"""Cross-section aggregates for the global market dashboard (not contract skills)."""

from __future__ import annotations

from typing import Any

from ..domain.nanhua_constituents import LEAF_NANHUA_CODES, resolve_nanhua_index_for_item
from .board_products import product_change_5d

EXCLUDED_BOARDS = {"金融", "航运"}


def build_global_context(
    *,
    nanhua_indices: list[dict[str, Any]] | None,
    drivers: list[dict[str, Any]] | None,
    macro: dict[str, Any] | None,
    contract_items: list[dict[str, Any]] | None,
    board_product_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    board_indices = [row for row in (nanhua_indices or []) if row.get("group") != "总指数"]
    lead = _pick_lead(nanhua_indices or [])
    return {
        "lead": lead,
        "nanhua_indices": nanhua_indices or [],
        "board_indices": board_indices,
        "drivers": drivers or [],
        "driver_map": {row["id"]: row for row in (drivers or []) if row.get("id")},
        "macro": macro or {},
        "contract_items": contract_items or [],
        "board_product_matrix": board_product_matrix or {},
        "board_stats": build_board_stats(contract_items or [], board_indices),
    }


def build_board_stats(
    items: list[dict[str, Any]],
    board_indices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index_by_code = {
        str(row.get("index_code") or row.get("id", "").replace(".NH", "")): row
        for row in board_indices
    }
    buckets: dict[str, list[dict[str, Any]]] = {
        code: [] for code in LEAF_NANHUA_CODES
    }

    for item in items:
        board = item.get("board") or "未分类"
        if board in EXCLUDED_BOARDS:
            continue
        code = resolve_nanhua_index_for_item(item)
        if not code or code not in buckets:
            continue
        change_5d = product_change_5d(item)
        if change_5d is None:
            continue
        buckets[code].append(
            {
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "direction": item.get("direction") or "neutral",
                "change_5d": change_5d,
            }
        )

    rows: list[dict[str, Any]] = []
    for code, products in buckets.items():
        if not products:
            continue
        index_row = index_by_code.get(code) or {}
        index_weekly = (index_row.get("changes") or {}).get("5d")
        up = sum(1 for p in products if p["direction"] == "up")
        down = sum(1 for p in products if p["direction"] == "down")
        neutral = len(products) - up - down
        changes = [p["change_5d"] for p in products]
        median_5d = _median(changes)
        top = max(products, key=lambda p: p["change_5d"])
        bottom = min(products, key=lambda p: p["change_5d"])
        same_dir_ratio = up / len(products) if products else 0.0
        divergence = None
        if index_weekly is not None and median_5d is not None:
            divergence = round(median_5d - float(index_weekly), 4)
        rows.append(
            {
                "code": code,
                "name": index_row.get("name") or code,
                "index_change_5d": index_weekly,
                "product_count": len(products),
                "up": up,
                "down": down,
                "neutral": neutral,
                "same_dir_ratio": round(same_dir_ratio, 4),
                "median_change_5d": median_5d,
                "top_product": top,
                "bottom_product": bottom,
                "index_divergence": divergence,
            }
        )
    return rows


def _pick_lead(nanhua_indices: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in nanhua_indices:
        if row.get("index_code") == "NHCI" or row.get("id") == "NHCI.NH":
            return row
    return nanhua_indices[0] if nanhua_indices else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 4)
