"""Product-specific fundamental framework knowledge skill."""

from __future__ import annotations

from typing import Any

from ...research.registry import get_product_playbook
from ...research.playbook_runner import run_framework_playbook
from ._context import framework_context

SKILL_ID = "product_framework"
TITLE = "品种框架"
PRIORITY = 47


def analyze(
    *,
    meta: dict[str, Any] | None,
    analyzers: list[dict[str, Any]],
    state: str,
    level: str,
    direction: str,
    score: int,
) -> dict[str, Any]:
    ctx = framework_context(meta=meta, analyzers=analyzers, state=state, level=level, direction=direction, score=score)
    symbol = ctx["meta"].get("symbol")
    playbook = get_product_playbook(symbol)
    if not playbook:
        return run_framework_playbook(
            None,
            skill_id=SKILL_ID,
            title=TITLE,
            priority=PRIORITY - 5,
            state=ctx["state"],
            level=ctx["level"],
            direction=ctx["direction"],
            score=ctx["score"],
            skills_by_id=ctx["skills_by_id"],
        )
    return run_framework_playbook(
        playbook,
        skill_id=SKILL_ID,
        title=playbook.get("name") or TITLE,
        priority=PRIORITY,
        state=ctx["state"],
        level=ctx["level"],
        direction=ctx["direction"],
        score=ctx["score"],
        skills_by_id=ctx["skills_by_id"],
    )
