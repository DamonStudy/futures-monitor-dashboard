"""Global market overview data package."""

from __future__ import annotations

from .board_products import build_board_product_matrix, board_product_matrix_invalid
from .index_constituents import index_catalog_entry
from .overview import build_global_overview, build_narrative, _nanhua_lead
from .schema import GLOBAL_SNAPSHOT_SCHEMA_VERSION
from .skills import run_global_market_skills


def enrich_index_row(row: dict) -> None:
    index_id = row.get("id")
    if not index_id:
        return
    catalog = index_catalog_entry(index_id)
    row.setdefault("index_code", catalog.get("index_code"))
    row.setdefault("series_id", catalog.get("series_id"))
    row.setdefault("series_name", catalog.get("series_name"))
    row.setdefault("level", catalog.get("level") or row.get("group"))


def hydrate_global_snapshot(data: dict, contract_snapshot: dict | None = None) -> dict:
    """Backfill index metadata and refresh narrative for older snapshots."""
    _backfill_nanhua_indices(data)

    for row in data.get("nanhua_indices") or []:
        enrich_index_row(row)

    nanhua_indices = data.get("nanhua_indices") or []
    lead = data.get("lead")
    if not lead or str(lead.get("id", "")).endswith(".CCI"):
        lead = _nanhua_lead(nanhua_indices)
        data["lead"] = lead

    board_indices = [row for row in nanhua_indices if row.get("group") != "总指数"]
    items = (contract_snapshot or {}).get("items") or data.get("contract_items") or []
    board_product_matrix = data.get("board_product_matrix")
    if items and _board_product_matrix_needs_rebuild(board_product_matrix):
        board_product_matrix = build_board_product_matrix(items, nanhua_indices)
        data["board_product_matrix"] = board_product_matrix

    skill_pack = run_global_market_skills(
        nanhua_indices=nanhua_indices,
        drivers=data.get("drivers") or [],
        macro=data.get("macro"),
        contract_items=items,
        board_product_matrix=board_product_matrix,
    )
    data["narrative"] = skill_pack.get("narrative") or build_narrative(
        lead,
        board_indices,
        data.get("drivers") or [],
        data.get("macro"),
        board_stats=skill_pack.get("context", {}).get("board_stats"),
    )
    data["global_skills"] = skill_pack.get("skills") or []
    data.pop("commodity_indices", None)
    data.pop("contract_items", None)
    data["schema_version"] = GLOBAL_SNAPSHOT_SCHEMA_VERSION
    return data


def _board_product_matrix_needs_rebuild(matrix: dict | None) -> bool:
    return board_product_matrix_invalid(matrix)


def _backfill_nanhua_indices(data: dict) -> None:
    if data.get("nanhua_indices"):
        return
    import os

    if not os.getenv("TUSHARE_TOKEN"):
        return
    try:
        from .overview import fetch_nanhua_indices

        data["nanhua_indices"] = fetch_nanhua_indices()
    except Exception as exc:
        errors = data.setdefault("errors", [])
        if isinstance(errors, list):
            errors.append({"source": "nanhua_indices", "message": str(exc)})


__all__ = ["build_global_overview", "hydrate_global_snapshot"]
