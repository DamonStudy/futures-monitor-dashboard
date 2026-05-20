"""Supplement contract specs from AkShare when TqSdk quote fields are empty."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


def load_akshare_specs() -> dict[str, dict[str, Any]]:
    try:
        import akshare as ak

        df = ak.futures_fees_info()
    except Exception:
        return {"contracts": {}, "products": {}}

    contracts: dict[str, dict[str, Any]] = {}
    product_rows: dict[str, list[dict[str, Any]]] = {}
    for _, row in df.iterrows():
        contract_code = str(row.iloc[1]).strip()
        product_code = str(row.iloc[3]).strip()
        if not contract_code or not product_code:
            continue
        item = {
            "exchange": str(row.iloc[0]).strip(),
            "contract_code": contract_code,
            "product_code": product_code,
            "volume_multiple": number(row.iloc[5]),
            "price_tick": number(row.iloc[6]),
            "last_price": number(row.iloc[19]),
            "volume": number(row.iloc[20]),
            "open_interest": number(row.iloc[21]),
            "margin": max_number(row.iloc[25], row.iloc[26]),
            "contract_value": number(row.iloc[27]),
            "tick_value": number(row.iloc[28]),
            "spec_source": "AkShare",
        }
        contracts[contract_code.lower()] = item
        product_rows.setdefault(product_code.lower(), []).append(item)

    products = {
        code: max(rows, key=lambda x: ((x.get("open_interest") or 0), (x.get("volume") or 0)))
        for code, rows in product_rows.items()
    }
    return {"contracts": contracts, "products": products}


def enrich_quote_with_specs(
    meta: dict[str, Any],
    quote: dict[str, Any],
    specs: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    enriched = dict(quote)
    spec = find_spec(meta, quote, specs or {})
    if not spec:
        return enriched

    for key in ("volume_multiple", "price_tick", "margin", "contract_value", "tick_value"):
        if is_empty(enriched.get(key)) and not is_empty(spec.get(key)):
            enriched[key] = spec[key]
    enriched.setdefault("spec_source", spec.get("spec_source"))
    if is_empty(enriched.get("underlying_symbol")):
        enriched["underlying_symbol"] = f"{spec.get('exchange')}.{spec.get('contract_code')}"
    return enriched


def find_spec(
    meta: dict[str, Any],
    quote: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    contract_code = extract_contract_code(quote.get("underlying_symbol") or quote.get("symbol"))
    if contract_code:
        item = specs.get("contracts", {}).get(contract_code.lower())
        if item:
            return item

    product_code = extract_product_code(meta.get("symbol"))
    if product_code:
        return specs.get("products", {}).get(product_code.lower())
    return None


def extract_contract_code(symbol: Any) -> str | None:
    if not symbol:
        return None
    text = str(symbol).split(".")[-1]
    match = re.search(r"([A-Za-z]+[0-9]{3,4})$", text)
    return match.group(1) if match else None


def extract_product_code(symbol: Any) -> str | None:
    if not symbol:
        return None
    return str(symbol).split(".")[-1]


def number(value: Any) -> float | None:
    result = pd.to_numeric(value, errors="coerce")
    if pd.isna(result):
        return None
    return float(result)


def max_number(*values: Any) -> float | None:
    nums = [number(value) for value in values]
    nums = [value for value in nums if value is not None]
    return max(nums) if nums else None


def is_empty(value: Any) -> bool:
    if value is None or value == "":
        return True
    try:
        return pd.isna(value)
    except TypeError:
        return False
