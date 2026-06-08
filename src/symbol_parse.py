"""Symbol parsing helpers shared across data and research modules."""

from __future__ import annotations

import re


def parse_product_symbol(symbol: str | None) -> tuple[str | None, str | None]:
    if not symbol:
        return None, None
    tail = symbol.split("@", 1)[-1]
    parts = tail.split(".")
    if len(parts) == 2:
        return parts[0], parts[1]
    contract = parts[-1]
    match = re.match(r"^([A-Za-z]+)", contract)
    if match:
        return None, match.group(1)
    return None, None


def product_id_from_symbol(symbol: str | None) -> str | None:
    _, product = parse_product_symbol(symbol)
    return product.lower() if product else None
