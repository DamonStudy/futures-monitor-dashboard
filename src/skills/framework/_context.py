"""Shared context helpers for framework knowledge skills."""

from __future__ import annotations

from typing import Any

from ...analyzers import ANALYZER_IDS


def analyzers_by_id(analyzers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in analyzers if item.get("id") in ANALYZER_IDS}


def framework_context(
    *,
    meta: dict[str, Any] | None,
    analyzers: list[dict[str, Any]],
    state: str,
    level: str,
    direction: str,
    score: int,
) -> dict[str, Any]:
    by_id = analyzers_by_id(analyzers)
    return {
        "meta": meta or {},
        "analyzers_by_id": by_id,
        "skills_by_id": by_id,  # legacy alias for playbook runner
        "state": state,
        "level": level,
        "direction": direction,
        "score": score,
    }
