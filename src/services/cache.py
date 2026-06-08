"""Snapshot cache read/write and hydration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..analyzers.directional_matrix import build_direction_matrix, month_from_day
from ..domain.nanhua_boards import resolve_nanhua_board
from ..global_market.board_products import board_product_matrix_invalid
from ..global_market.schema import GLOBAL_SNAPSHOT_SCHEMA_VERSION
from ..global_market import hydrate_global_snapshot
from ..trading_hours import hydrate_item_session


def read_json_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_is_today(data: dict[str, Any]) -> bool:
    refreshed_at = data.get("refreshed_at")
    if not refreshed_at:
        return False
    try:
        return datetime.strptime(refreshed_at, "%Y-%m-%d %H:%M:%S").date() == datetime.now().date()
    except ValueError:
        return False


def cache_has_analysis(data: dict[str, Any]) -> bool:
    items = data.get("items") or []
    if not items:
        return False
    for item in items[:5]:
        if item.get("analyzers"):
            continue
        if item.get("skills"):
            continue
        return False
    return True


def cache_has_skills(data: dict[str, Any]) -> bool:
    return cache_has_analysis(data)


def _matrix_needs_rebuild(matrix: dict[str, Any] | None) -> bool:
    if not matrix:
        return True
    keys = {row.get("key") for row in (matrix.get("periods") or []) if row.get("key")}
    return "hour" in keys or keys != {"day", "week", "month"}


def hydrate_direction_matrices(data: dict[str, Any]) -> None:
    for item in data.get("items") or []:
        if item.get("direction_matrix") and not _matrix_needs_rebuild(item["direction_matrix"]):
            continue
        charts = item.get("charts") or {}
        day = pd.DataFrame(charts.get("day") or [])
        week = pd.DataFrame(charts.get("week") or [])
        if day.empty and week.empty:
            continue
        item["direction_matrix"] = build_direction_matrix(
            {
                "day": day,
                "week": week,
                "month": month_from_day(day),
            }
        )


def hydrate_sessions(data: dict[str, Any]) -> None:
    for item in data.get("items") or []:
        hydrate_item_session(item)


def _strip_hour_period(skill: dict[str, Any]) -> None:
    allowed = {"day", "week"}
    signals = skill.get("signals")
    if isinstance(signals, list):
        skill["signals"] = [row for row in signals if row.get("period") in allowed or not row.get("period")]
    levels = skill.get("levels")
    if isinstance(levels, list):
        skill["levels"] = [row for row in levels if row.get("period") in allowed or not row.get("period")]


def sanitize_skill_periods(data: dict[str, Any]) -> None:
    for item in data.get("items") or []:
        for key in ("analyzers", "skills"):
            for skill in item.get(key) or []:
                if isinstance(skill, dict):
                    _strip_hour_period(skill)


def hydrate_nanhua_boards(data: dict[str, Any]) -> None:
    for item in data.get("items") or []:
        if item.get("nanhua_board"):
            continue
        item.update(resolve_nanhua_board(item.get("board")))


def read_contract_snapshot(cache_file: Path) -> dict[str, Any] | None:
    if not cache_file.exists():
        return None
    data = read_json_cache(cache_file)
    if data:
        sanitize_skill_periods(data)
        hydrate_direction_matrices(data)
        hydrate_sessions(data)
        hydrate_nanhua_boards(data)
    return data


def global_schema_outdated(data: dict[str, Any] | None) -> bool:
    if not data:
        return True
    if data.get("schema_version", 0) < GLOBAL_SNAPSHOT_SCHEMA_VERSION:
        return True
    narrative = data.get("narrative")
    if not isinstance(narrative, dict) or narrative.get("version") != 2:
        return True
    if "board_product_matrix" not in data:
        return True
    if "global_skills" not in data:
        return True
    return False


def global_board_matrix_stale(
    data: dict[str, Any] | None,
    contract_snapshot: dict[str, Any] | None = None,
) -> bool:
    items = (contract_snapshot or {}).get("items") or []
    if not items:
        return False
    matrix = (data or {}).get("board_product_matrix")
    if not matrix or matrix.get("status") != "ok":
        return True
    return not any((row.get("product_count") or 0) > 0 for row in (matrix.get("rows") or []))


def global_snapshot_should_persist(
    raw: dict[str, Any] | None,
    hydrated: dict[str, Any] | None,
    contract_snapshot: dict[str, Any] | None = None,
) -> bool:
    if not raw or not hydrated:
        return False
    if global_schema_outdated(raw):
        return True
    if global_board_matrix_stale(raw, contract_snapshot) and not global_board_matrix_stale(
        hydrated, contract_snapshot
    ):
        return True
    if board_product_matrix_invalid(raw.get("board_product_matrix")) and not board_product_matrix_invalid(
        hydrated.get("board_product_matrix")
    ):
        return True
    return False


def global_cache_reusable(
    data: dict[str, Any] | None,
    contract_snapshot: dict[str, Any] | None = None,
) -> bool:
    if not data or not cache_is_today(data):
        return False
    if not data.get("nanhua_indices"):
        return False
    if global_schema_outdated(data):
        return False
    if board_product_matrix_invalid(data.get("board_product_matrix")):
        return False
    return not global_board_matrix_stale(data, contract_snapshot)


def read_global_snapshot(cache_file: Path, contract_cache_file: Path | None = None) -> dict[str, Any] | None:
    data = read_json_cache(cache_file)
    if data:
        contract_data = read_contract_snapshot(contract_cache_file) if contract_cache_file else None
        hydrate_global_snapshot(data, contract_data)
    return data
