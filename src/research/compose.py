"""Compose insight from data analyzers and playbook stack."""

from __future__ import annotations

from typing import Any

from ..analyzers import ANALYZER_IDS
from .playbook_runner import build_core_hits, layer_label, signals_for_step
from .registry import resolve_personas, resolve_playbook_stack
from .selector import select_steps
from .synthesis import build_narrative

LEVEL_WEIGHT = {"critical": 4, "watch": 3, "info": 2}
MAX_SIGNALS = 18
MACRO_ANALYZER_IDS = frozenset({"macro_regime"})


def _product_insight_stack(stack: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Variety insight focuses on price/volume and product logic — not shared macro."""
    return [
        playbook
        for playbook in stack
        if not (playbook.get("_kind") == "layer" and playbook.get("id") == "macro")
    ]


def compose_insight(
    *,
    meta: dict[str, Any] | None,
    analyzers: list[dict[str, Any]],
    state: str,
    level: str,
    direction: str,
    score: int,
) -> dict[str, Any]:
    meta = meta or {}
    stack = _product_insight_stack(resolve_playbook_stack(symbol=meta.get("symbol"), board=meta.get("board")))
    personas = resolve_personas(symbol=meta.get("symbol"), board=meta.get("board"))
    full_stack = stack + personas

    if not full_stack:
        return {
            "status": "unavailable",
            "summary": "暂无推理框架，请补充 Playbook。",
            "signals": [],
            "brief": {},
            "core_hits": [],
            "gaps": [],
            "judgment_note": "暂无 Playbook 配置。",
            "selected_steps": 0,
            "total_steps": 0,
            "personas": [],
        }

    analyzers_by_id = {item["id"]: item for item in analyzers if item.get("id") in ANALYZER_IDS}
    selected = select_steps(
        full_stack,
        state=state,
        level=level,
        direction=direction,
        score=score,
        analyzers_by_id=analyzers_by_id,
        symbol=meta.get("symbol"),
        board=meta.get("board"),
    )

    chain_signals: list[dict[str, Any]] = []
    linked_steps = 0
    evidence_signals: list[dict[str, Any]] = []

    for item in selected:
        playbook = item["playbook"]
        if playbook.get("_kind") == "layer" and playbook.get("id") == "macro":
            continue
        step = item["step"]
        label = layer_label(playbook)
        step_signals = [
            sig
            for sig in signals_for_step(step, analyzers_by_id, label)
            if not _is_macro_signal(sig)
        ]
        if step_signals:
            linked_steps += 1
            evidence_signals.extend(step_signals)
            chain_signals.extend(step_signals)

    chain_signals.sort(key=lambda item: LEVEL_WEIGHT.get(item.get("level"), 1), reverse=True)
    core_hits = build_core_hits(evidence_signals)
    gaps: list[str] = []
    narrative = build_narrative(
        selected=selected,
        state=state,
        level=level,
        direction=direction,
        score=score,
        analyzers_by_id=analyzers_by_id,
    )
    triggers = _top_triggers(analyzers)
    brief = {
        **narrative,
        "triggers": triggers,
    }
    if personas:
        persona_names = [p.get("name") or p.get("id") for p in personas]
        brief["personas"] = persona_names

    return {
        "status": "ok",
        "summary": _build_summary(meta, linked_steps, len(core_hits), len(gaps), personas),
        "signals": chain_signals[:MAX_SIGNALS],
        "brief": brief,
        "core_hits": core_hits,
        "gaps": gaps,
        "judgment_note": _judgment_note(core_hits, gaps),
        "selected_steps": len(selected),
        "total_steps": sum(len(p.get("reasoning_chain") or []) for p in full_stack),
        "personas": [p.get("id") for p in personas],
    }


def _is_macro_signal(signal: dict[str, Any]) -> bool:
    text = f"{signal.get('name') or ''} {signal.get('interpretation') or ''}"
    if any(token in text for token in ("非农", "ISM", "GDP", "CPI", "PPI", "国债收益率", "中间价", "FOMC", "宏观")):
        return True
    source = str(signal.get("source") or "")
    return source in MACRO_ANALYZER_IDS


def _top_triggers(analyzers: list[dict[str, Any]], limit: int = 3) -> list[str]:
    strongest = sorted(
        (
            sig | {"source": module["id"]}
            for module in analyzers
            if module.get("id") not in MACRO_ANALYZER_IDS
            for sig in module.get("signals", [])
            if not _is_macro_signal(sig)
        ),
        key=lambda item: LEVEL_WEIGHT.get(item.get("level"), 1),
        reverse=True,
    )
    return [f"{item['source']} · {item['name']}" for item in strongest[:limit]]


def _judgment_note(core_hits: list[dict[str, Any]], gaps: list[str]) -> str:
    hit_count = len(core_hits)
    if hit_count:
        names = []
        for hit in core_hits[:3]:
            raw = str(hit.get("name") or "").strip()
            if not raw:
                continue
            names.append(raw.split("·")[-1].strip() or raw)
        lead = f"已命中 {hit_count} 项"
        if names:
            lead += f"（{'、'.join(names)}）"
        return f"{lead}，当前以盘面与品种逻辑为主。"
    return "暂无可验证盘面命中，建议刷新数据或查看量价技术栏。"


def _build_summary(
    meta: dict[str, Any],
    linked_steps: int,
    hit_count: int,
    gap_count: int,
    personas: list[dict[str, Any]],
) -> str:
    name = meta.get("name") or "该品种"
    parts = [f"{name}：命中 {hit_count} 条核心证据"]
    if linked_steps:
        parts.append(f"覆盖 {linked_steps} 个分析步骤")
    if gap_count:
        parts.append(f"尚缺 {gap_count} 项无法下结论")
    if personas:
        parts.append(f"叠加 {len(personas)} 个外部视角")
    return "，".join(parts) + "。"
