"""Knowledge skills — playbook-driven SOP for research reasoning."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..analyzers import analyze_all
from . import insight, persona
from .framework import board_framework, macro_framework, product_framework, technical_framework


def analyze_knowledge(
    *,
    analyzers: list[dict[str, Any]],
    meta: dict[str, Any] | None,
    state: str,
    level: str,
    direction: str,
    score: int,
) -> list[dict[str, Any]]:
    ctx = {
        "meta": meta,
        "analyzers": analyzers,
        "state": state,
        "level": level,
        "direction": direction,
        "score": score,
    }
    framework_modules = [
        macro_framework(**ctx),
        technical_framework(**ctx),
        board_framework(**ctx),
        product_framework(**ctx),
    ]
    persona_modules = persona.analyze_all(**ctx)
    insight_module = insight.analyze(
        meta=meta,
        analyzers=analyzers,
        state=state,
        level=level,
        direction=direction,
        score=score,
    )
    return framework_modules + persona_modules + [insight_module]


def analyze_contract(
    *,
    periods: dict[str, pd.DataFrame],
    state: str,
    level: str,
    direction: str,
    score: int,
    chain_quotes: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    quote: dict[str, Any] | None = None,
    include_external: bool = True,
    macro_context: dict[str, Any] | None = None,
    board_peers: list[dict[str, Any]] | None = None,
    boards_summary: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Run data analyzers then knowledge skills; return both lists separately."""
    analyzer_modules = analyze_all(
        periods=periods,
        chain_quotes=chain_quotes,
        meta=meta,
        quote=quote,
        include_external=include_external,
        macro_context=macro_context,
        direction=direction,
        board_peers=board_peers,
        boards_summary=boards_summary,
    )
    knowledge_modules = analyze_knowledge(
        analyzers=analyzer_modules,
        meta=meta,
        state=state,
        level=level,
        direction=direction,
        score=score,
    )
    return {
        "analyzers": sorted(analyzer_modules, key=lambda item: item.get("priority", 0), reverse=True),
        "skills": sorted(knowledge_modules, key=lambda item: item.get("priority", 0), reverse=True),
    }
