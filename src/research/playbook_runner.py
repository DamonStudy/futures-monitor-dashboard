"""Execute a single Playbook as a knowledge skill."""

from __future__ import annotations

from typing import Any

from ..analyzers.schema import signal
from ..skills.schema import skill_result
from .links import step_analyzer_links
from .selector import select_steps

LEVEL_WEIGHT = {"critical": 4, "watch": 3, "info": 2}


def layer_label(playbook: dict[str, Any]) -> str:
    kind = playbook.get("_kind")
    if kind == "layer":
        return playbook.get("name") or playbook.get("id") or "通用"
    if kind == "board":
        return f"{playbook.get('name') or playbook.get('id') or '板块'}·基本面"
    if kind == "product":
        return playbook.get("name") or playbook.get("id") or "品种"
    if kind == "persona":
        return playbook.get("name") or playbook.get("id") or "视角"
    return playbook.get("name") or "分析"


def run_framework_playbook(
    playbook: dict[str, Any] | None,
    *,
    skill_id: str,
    title: str,
    priority: int,
    state: str,
    level: str,
    direction: str,
    score: int,
    analyzers_by_id: dict[str, dict[str, Any]] | None = None,
    skills_by_id: dict[str, dict[str, Any]] | None = None,
    symbol: str | None = None,
    board: str | None = None,
) -> dict[str, Any]:
    by_id = analyzers_by_id or skills_by_id or {}
    if not playbook:
        return skill_result(skill_id, title, "暂无框架配置。", status="unavailable", priority=max(priority - 10, 20))

    label = layer_label(playbook)
    selected = select_steps(
        [playbook],
        state=state,
        level=level,
        direction=direction,
        score=score,
        analyzers_by_id=by_id,
        symbol=symbol,
        board=board,
        max_steps=8,
    )
    signals: list[dict[str, Any]] = []
    linked = 0
    for item in selected:
        step = item["step"]
        step_signals = signals_for_step(step, by_id, label)
        if step_signals:
            linked += 1
            signals.extend(step_signals)
        else:
            signals.append(
                signal(
                    f"{label}·{step.get('title', '分析')}",
                    step_guidance(step, playbook.get("_kind")),
                    level="info",
                )
            )

    gaps = build_gaps([playbook], by_id) if playbook.get("_kind") in {"board", "product", "persona"} else []
    summary = f"{title}：选用 {len(selected)} 步"
    if linked:
        summary += f"，{linked} 步已接盘面"

    result = skill_result(
        skill_id,
        title,
        summary,
        priority=priority,
        signals=signals[:10],
    )
    result["gaps"] = gaps
    result["playbook_id"] = playbook.get("id")
    result["selected_steps"] = len(selected)
    return result


def signals_for_step(
    step: dict[str, Any],
    analyzers_by_id: dict[str, dict[str, Any]],
    layer_label_text: str,
) -> list[dict[str, Any]]:
    links = step_analyzer_links(step)
    if not links:
        return []

    collected: list[dict[str, Any]] = []
    for analyzer_id in links:
        module = analyzers_by_id.get(analyzer_id)
        if not module:
            continue
        ranked = sorted(
            module.get("signals", []),
            key=lambda item: LEVEL_WEIGHT.get(item.get("level"), 1),
            reverse=True,
        )
        for item in ranked[:2]:
            collected.append(
                signal(
                    f"{layer_label_text}·{step.get('title', '分析')}·{item.get('name', '信号')}",
                    f"{item.get('interpretation', '')}",
                    level=item.get("level", "info"),
                    period=item.get("period"),
                    value=item.get("value"),
                    threshold=item.get("threshold"),
                )
            )
    return collected


def step_guidance(step: dict[str, Any], kind: str | None) -> str:
    focus = "、".join(step.get("focus") or [])
    questions = step.get("questions") or []
    fallback = step.get("fallback") or ""
    parts: list[str] = []
    if focus:
        parts.append(f"关注 {focus}")
    if questions:
        parts.append(questions[0])
    if fallback:
        parts.append(fallback)
    if kind == "persona":
        parts.append("（大V视角，需与盘面及基本面交叉验证）")
    elif kind in {"board", "product"} and not step_analyzer_links(step):
        parts.append("（基本面待接入）")
    return "；".join(parts) if parts else "按框架跟踪"


def linked_signals(links: list[str], analyzers_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for analyzer_id in links:
        module = analyzers_by_id.get(analyzer_id)
        if module:
            signals.extend(module.get("signals", []))
    return signals


def build_gaps(stack: list[dict[str, Any]], analyzers_by_id: dict[str, dict[str, Any]], limit: int = 6) -> list[str]:
    gaps: list[str] = []
    for playbook in stack:
        if playbook.get("_kind") not in {"product", "board", "persona"}:
            continue
        label = layer_label(playbook)
        for step in playbook.get("reasoning_chain", []):
            title = step.get("title") or "分析步骤"
            links = step_analyzer_links(step)
            focus = "、".join((step.get("focus") or [])[:4])

            if not links:
                text = f"{label}·{title}：未接入"
                if focus:
                    text += f"（{focus}）"
                gaps.append(text)
                continue

            if not linked_signals(links, analyzers_by_id):
                gaps.append(f"{label}·{title}：待盘面验证")

    return gaps[:limit]


def build_core_hits(evidence_signals: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    ranked = sorted(
        evidence_signals,
        key=lambda item: LEVEL_WEIGHT.get(item.get("level"), 1),
        reverse=True,
    )
    for item in ranked:
        interpretation = str(item.get("interpretation") or "")
        text = interpretation.split("（")[0].strip() or interpretation
        name = str(item.get("name") or "")
        short = name.split("·")[-1] if "·" in name else name
        dedupe_key = f"{short}|{text}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        hits.append(
            {
                "name": name,
                "text": text,
                "level": item.get("level", "info"),
                "period": item.get("period"),
                "value": item.get("value"),
            }
        )
        if len(hits) >= limit:
            break
    return hits
