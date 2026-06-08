"""Legacy research_lens wrapper — delegates to compose_insight."""

from __future__ import annotations

from typing import Any

from ..analyzers import ANALYZER_IDS
from ..skills.schema import skill_result
from .compose import compose_insight

SKILL_ID = "research_lens"
TITLE = "研究员思维链"


def analyze(
    *,
    meta: dict[str, Any] | None,
    skills: list[dict[str, Any]] | None = None,
    analyzers: list[dict[str, Any]] | None = None,
    state: str,
    level: str,
    direction: str,
    score: int = 0,
) -> dict[str, Any]:
    data_analyzers = analyzers or [
        item for item in (skills or []) if item.get("id") in ANALYZER_IDS and item.get("kind") != "skill"
    ]
    payload = compose_insight(
        meta=meta,
        analyzers=data_analyzers,
        state=state,
        level=level,
        direction=direction,
        score=score,
    )
    if payload.get("status") == "unavailable":
        return skill_result(SKILL_ID, TITLE, payload.get("summary") or "暂无框架。", status="unavailable", priority=35)

    result = skill_result(
        SKILL_ID,
        TITLE,
        payload["summary"],
        priority=48,
        signals=payload.get("signals") or [],
    )
    result["brief"] = payload.get("brief") or {}
    result["narrative"] = payload.get("brief") or {}
    result["core_hits"] = payload.get("core_hits") or []
    result["gaps"] = payload.get("gaps") or []
    result["judgment_note"] = payload.get("judgment_note") or ""
    result["selected_steps"] = payload.get("selected_steps", 0)
    result["total_steps"] = payload.get("total_steps", 0)
    return result
