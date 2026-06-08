"""Exclusive Nanhua leaf index <-> monitored contract mapping."""

from __future__ import annotations

from typing import Any

from ..contracts import BOARDS
from .nanhua_boards import INTERNAL_BOARD_TO_NANHUA

# Composite indices aggregate leaf sectors — no exclusive contract bucket.
COMPOSITE_NANHUA_CODES = frozenset({"NHII", "NHMI"})

LEAF_NANHUA_CODES = frozenset({"NHFI", "NHNFI", "NHECI", "NHAI", "NHPMI"})


def _build_product_maps() -> tuple[dict[str, str], dict[str, str], dict[str, list[dict[str, str]]]]:
    symbol_to_code: dict[str, str] = {}
    name_to_code: dict[str, str] = {}
    index_to_products: dict[str, list[dict[str, str]]] = {code: [] for code in LEAF_NANHUA_CODES}

    for board, contracts in BOARDS.items():
        code, _label = INTERNAL_BOARD_TO_NANHUA.get(board, (None, board))
        if not code or code in COMPOSITE_NANHUA_CODES:
            continue
        for name, symbol in contracts:
            symbol_to_code[symbol] = code
            name_to_code[name] = code
            index_to_products[code].append({"name": name, "symbol": symbol})

    return symbol_to_code, name_to_code, index_to_products


SYMBOL_TO_NANHUA_INDEX, NAME_TO_NANHUA_INDEX, NANHUA_INDEX_PRODUCTS = _build_product_maps()


def resolve_nanhua_index_for_item(item: dict[str, Any]) -> str | None:
    """Return the exclusive leaf Nanhua index code for a monitored contract."""
    symbol = str(item.get("actual_symbol") or item.get("symbol") or "").strip()
    if symbol and symbol in SYMBOL_TO_NANHUA_INDEX:
        return SYMBOL_TO_NANHUA_INDEX[symbol]

    name = str(item.get("name") or "").strip()
    if name and name in NAME_TO_NANHUA_INDEX:
        return NAME_TO_NANHUA_INDEX[name]

    board = item.get("board") or "未分类"
    code, _label = INTERNAL_BOARD_TO_NANHUA.get(board, (None, None))
    if code in COMPOSITE_NANHUA_CODES:
        return None
    return code


def nanhua_index_product_names(index_code: str) -> list[str]:
    return [row["name"] for row in NANHUA_INDEX_PRODUCTS.get(index_code, [])]


def board_product_matrix_invalid(matrix: dict[str, Any] | None) -> bool:
    """Detect legacy overlap layout or composite rows incorrectly filled."""
    if not matrix or matrix.get("status") != "ok":
        return True

    seen: set[str] = set()
    for row in matrix.get("rows") or []:
        code = row.get("code")
        if code in COMPOSITE_NANHUA_CODES or row.get("composite"):
            return True
        for product in row.get("products") or []:
            key = str(product.get("symbol") or product.get("name") or "")
            if not key:
                continue
            if key in seen:
                return True
            seen.add(key)
    return False
