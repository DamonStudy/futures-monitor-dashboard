"""Persona (influencer viewpoint) knowledge skills."""

from __future__ import annotations

from typing import Any

from ..research.playbook_runner import run_framework_playbook
from ..research.registry import resolve_personas
from .framework._context import framework_context


def analyze_all(
    *,
    meta: dict[str, Any] | None,
    analyzers: list[dict[str, Any]],
    state: str,
    level: str,
    direction: str,
    score: int,
) -> list[dict[str, Any]]:
    ctx = framework_context(meta=meta, analyzers=analyzers, state=state, level=level, direction=direction, score=score)
    personas = resolve_personas(symbol=ctx["meta"].get("symbol"), board=ctx["meta"].get("board"))
    modules: list[dict[str, Any]] = []
    for index, playbook in enumerate(personas):
        skill_id = f"persona_{playbook.get('id')}"
        title = playbook.get("name") or skill_id
        modules.append(
            run_framework_playbook(
                playbook,
                skill_id=skill_id,
                title=f"视角·{title}",
                priority=40 - index,
                state=ctx["state"],
                level=ctx["level"],
                direction=ctx["direction"],
                score=ctx["score"],
                skills_by_id=ctx["analyzers_by_id"],
                symbol=ctx["meta"].get("symbol"),
                board=ctx["meta"].get("board"),
            )
        )
    return modules
