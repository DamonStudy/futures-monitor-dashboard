"""Global market knowledge skills — separate from contract-level src/skills/."""

from __future__ import annotations

from typing import Any

from ..aggregates import build_global_context
from .board_landscape import analyze as board_landscape
from .macro_regime import analyze as macro_regime
from .market_insight import analyze as market_insight


GLOBAL_SKILL_IDS = ("macro_regime", "board_landscape", "market_insight")


def run_global_market_skills(
    *,
    nanhua_indices: list[dict[str, Any]] | None,
    drivers: list[dict[str, Any]] | None,
    macro: dict[str, Any] | None,
    contract_items: list[dict[str, Any]] | None = None,
    board_product_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run market-level skills and compose the dashboard narrative."""
    ctx = build_global_context(
        nanhua_indices=nanhua_indices,
        drivers=drivers,
        macro=macro,
        contract_items=contract_items,
        board_product_matrix=board_product_matrix,
    )
    skills = [
        macro_regime(ctx),
        board_landscape(ctx),
    ]
    insight = market_insight(ctx, skills)
    skills.append(insight)
    return {
        "skills": skills,
        "insight": insight,
        "narrative": insight.get("narrative") or _empty_narrative(),
        "context": {
            "board_stats": ctx.get("board_stats") or [],
            "board_stats_count": len(ctx.get("board_stats") or []),
            "contract_count": len(ctx.get("contract_items") or []),
        },
    }


def _empty_narrative() -> dict[str, Any]:
    return {
        "version": 2,
        "sections": [
            {"key": "phenomenon", "title": "现象", "items": []},
            {"key": "mechanism", "title": "机制", "items": []},
            {"key": "verify", "title": "待验证", "items": []},
        ],
    }


__all__ = ["run_global_market_skills", "GLOBAL_SKILL_IDS"]
