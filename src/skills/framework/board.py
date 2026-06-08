"""Board-level fundamental framework knowledge skill."""

from __future__ import annotations

from typing import Any

from ...research.registry import get_board_playbook
from ...research.playbook_runner import run_framework_playbook
from ._context import framework_context

SKILL_ID = "board_framework"
TITLE = "板块框架"
PRIORITY = 46


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
    board = ctx["meta"].get("board")
    playbook = get_board_playbook(board) if board else None
    return run_framework_playbook(
        playbook,
        skill_id=SKILL_ID,
        title=TITLE if not playbook else f"{playbook.get('name', TITLE)}",
        priority=PRIORITY,
        state=ctx["state"],
        level=ctx["level"],
        direction=ctx["direction"],
        score=ctx["score"],
        skills_by_id=ctx["skills_by_id"],
    )
