"""Select playbook steps by relevance to current market data."""

from __future__ import annotations

from typing import Any

from ..symbol_parse import product_id_from_symbol
from .links import step_analyzer_links

LEVEL_WEIGHT = {"critical": 4, "watch": 3, "info": 2}

STATE_STEP_HINTS: dict[str, tuple[str, ...]] = {
    "突破": ("market", "trend", "volume_price", "pattern", "term", "supply", "demand"),
    "趋势": ("trend", "timeframe", "volume_price", "market", "supply", "demand"),
    "反转": ("pattern", "timeframe", "term", "demand", "inventory"),
    "震荡": ("timeframe", "pattern", "inventory", "regime", "spread"),
    "波动": ("volume_price", "pattern", "term"),
}


def select_steps(
    stack: list[dict[str, Any]],
    *,
    state: str,
    level: str,
    direction: str,
    score: int,
    analyzers_by_id: dict[str, dict[str, Any]] | None = None,
    skills_by_id: dict[str, dict[str, Any]] | None = None,
    symbol: str | None = None,
    board: str | None = None,
    max_steps: int = 12,
) -> list[dict[str, Any]]:
    """Return selected steps sorted by layer order, each enriched with score metadata."""
    by_id = analyzers_by_id or skills_by_id or {}
    product_id = product_id_from_symbol(symbol)
    scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
    for layer_index, playbook in enumerate(stack):
        for step in playbook.get("reasoning_chain", []):
            if not step_matches_scope(
                step,
                playbook_kind=str(playbook.get("_kind") or ""),
                board=board,
                product_id=product_id,
            ):
                continue
            relevance = score_step(
                playbook,
                step,
                state=state,
                level=level,
                direction=direction,
                score=score,
                analyzers_by_id=by_id,
            )
            scored.append((relevance, layer_index, playbook, step))

    if not scored:
        return []

    scored.sort(key=lambda item: item[0], reverse=True)
    threshold = _dynamic_threshold(scored, score)
    chosen: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
    for item in scored:
        if item[0] < threshold:
            continue
        chosen.append(item)
        if len(chosen) >= max_steps:
            break

    if not chosen:
        chosen = scored[: min(6, len(scored))]

    chosen = _ensure_layer_coverage(chosen, scored, stack)
    chosen.sort(key=lambda item: (item[1], -item[0]))

    return [
        {
            "playbook": playbook,
            "step": step,
            "score": relevance,
            "layer_index": layer_index,
        }
        for relevance, layer_index, playbook, step in chosen[:max_steps]
    ]


def score_step(
    playbook: dict[str, Any],
    step: dict[str, Any],
    *,
    state: str,
    level: str,
    direction: str,
    score: int,
    analyzers_by_id: dict[str, dict[str, Any]],
) -> float:
    relevance = 0.0
    kind = playbook.get("_kind")
    step_id = str(step.get("id") or "")
    links = step_analyzer_links(step)

    linked = _linked_signals(links, analyzers_by_id)
    if linked:
        relevance += 4.0
        top = max(LEVEL_WEIGHT.get(sig.get("level"), 1) for sig in linked)
        relevance += top * 0.75

    for hint in _state_hints(state):
        haystack = f"{step_id} {step.get('title', '')} {' '.join(step.get('focus') or [])}"
        if hint in state or hint in haystack:
            relevance += 1.5

    if direction != "neutral" and step_id in {"market", "term_position", "volume_price", "trend"}:
        relevance += 1.0

    if score >= 70 and kind in {"product", "board"}:
        relevance += 1.0

    if kind == "layer" and playbook.get("id") == "technical":
        relevance += 1.0 if _is_technical_state(state) or linked else 0.25

    if kind == "layer" and playbook.get("id") == "macro":
        if score < 55 or "震荡" in state or "中性" in state or "等待" in state:
            relevance += 1.25
        else:
            relevance += 0.35

    if kind in {"product", "board"} and not links:
        relevance += 0.75 if score >= 50 else 0.4

    if "大行情" in level or "候选" in level:
        relevance += 0.5

    return relevance


def _linked_signals(links: list[str], analyzers_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for analyzer_id in links:
        module = analyzers_by_id.get(analyzer_id)
        if module:
            signals.extend(module.get("signals", []))
    return signals


def _state_hints(state: str) -> tuple[str, ...]:
    hints: list[str] = []
    for key, ids in STATE_STEP_HINTS.items():
        if key in state:
            hints.extend(ids)
    return tuple(dict.fromkeys(hints))


def _is_technical_state(state: str) -> bool:
    return any(key in state for key in ("突破", "趋势", "反转", "震荡", "波动"))


def step_matches_scope(
    step: dict[str, Any],
    *,
    playbook_kind: str,
    board: str | None,
    product_id: str | None,
) -> bool:
    """Filter persona steps tagged with boards/products; other layers always match."""
    if playbook_kind != "persona":
        return True

    step_boards = [str(item) for item in step.get("boards") or []]
    step_products = [str(item).lower() for item in step.get("products") or []]
    if not step_boards and not step_products:
        return True

    if product_id and step_products:
        return product_id.lower() in step_products

    if board and step_boards:
        return board in step_boards

    if step_products:
        return False

    if step_boards:
        return False

    return True


def _dynamic_threshold(scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]], score: int) -> float:
    if not scored:
        return 1.0
    top = scored[0][0]
    base = 1.0 if score >= 55 else 0.75
    return min(base, top * 0.45)


def _ensure_layer_coverage(
    chosen: list[tuple[float, int, dict[str, Any], dict[str, Any]]],
    scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]],
    stack: list[dict[str, Any]],
) -> list[tuple[float, int, dict[str, Any], dict[str, Any]]]:
    chosen_keys = {(item[1], item[3].get("id")) for item in chosen}
    result = list(chosen)

    for layer_index, playbook in enumerate(stack):
        kind = playbook.get("_kind")
        if kind == "layer" and playbook.get("id") == "macro":
            continue
        if kind not in {"layer", "product", "board"}:
            continue
        has_layer = any(item[1] == layer_index for item in result)
        if has_layer:
            continue
        for item in scored:
            if item[1] != layer_index:
                continue
            key = (item[1], item[3].get("id"))
            if key not in chosen_keys:
                result.append(item)
                chosen_keys.add(key)
            break

    return result
