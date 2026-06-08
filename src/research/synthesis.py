"""Thread selected evidence and playbook knowledge into structured brief sections.

Copy tone: calm, explicit, pragmatic — see docs/product-preferences.md §解读话术风格.
"""

from __future__ import annotations

from typing import Any

from .links import step_analyzer_links

LEVEL_WEIGHT = {"critical": 4, "watch": 3, "info": 2}


def build_narrative(
    *,
    selected: list[dict[str, Any]],
    state: str,
    level: str,
    direction: str,
    score: int,
    analyzers_by_id: dict[str, dict[str, Any]] | None = None,
    skills_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    by_id = analyzers_by_id or skills_by_id or {}
    return {
        "headline": f"{state} · {level}",
        "evidence": _top_evidence(selected, by_id),
        "framework": _framework_hints(selected, by_id),
        "verify": _verify_points(selected),
    }


def narrative_to_text(brief: dict[str, Any]) -> str:
    """Compact single-line fallback for legacy consumers."""
    parts = [brief.get("headline") or ""]
    for key, label in (("evidence", "盘面证据"), ("framework", "研究视角"), ("verify", "待验证")):
        items = brief.get(key) or []
        if items:
            parts.append(f"{label}：" + "；".join(items[:3]))
    return "。".join(part for part in parts if part) + ("。" if parts else "")


def _top_evidence(selected: list[dict[str, Any]], analyzers_by_id: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[tuple[int, str]] = []
    seen: set[str] = set()
    for item in selected:
        step = item["step"]
        layer = _layer_label(item["playbook"])
        for analyzer_id in step_analyzer_links(step):
            module = analyzers_by_id.get(analyzer_id)
            if not module:
                continue
            for sig in module.get("signals", []):
                name = str(sig.get("name") or "信号")
                body = str(sig.get("interpretation") or "").split("（")[0].strip()
                text = f"{name}：{body}" if body else name
                dedupe = f"{name}|{body}"
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                weight = LEVEL_WEIGHT.get(sig.get("level"), 1)
                rows.append((weight, text))
    rows.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in rows[:4]]


def _framework_hints(selected: list[dict[str, Any]], analyzers_by_id: dict[str, dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    for item in selected:
        step = item["step"]
        if _linked_signals(step, analyzers_by_id):
            continue
        layer = _layer_label(item["playbook"])
        focus = "、".join((step.get("focus") or [])[:4])
        title = step.get("title") or ""
        if focus:
            hints.append(f"{layer}·{title}：关注 {focus}")
        elif title:
            hints.append(f"{layer}·{title}")
    return hints[:3]


def _verify_points(selected: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for item in selected:
        playbook = item["playbook"]
        for raw in playbook.get("confirmation") or []:
            if raw in seen:
                continue
            seen.add(raw)
            points.append(raw)
        if len(points) >= 2:
            break
    if len(points) < 2:
        for item in selected:
            playbook = item["playbook"]
            for raw in playbook.get("invalidation") or []:
                text = f"若 {raw}，则当前判断减弱"
                if text in seen:
                    continue
                seen.add(text)
                points.append(text)
                if len(points) >= 2:
                    break
    return points[:3]


def _linked_signals(step: dict[str, Any], analyzers_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for analyzer_id in step_analyzer_links(step):
        module = analyzers_by_id.get(analyzer_id)
        if module:
            signals.extend(module.get("signals", []))
    return signals


def _layer_label(playbook: dict[str, Any]) -> str:
    kind = playbook.get("_kind")
    if kind == "layer":
        return playbook.get("name") or playbook.get("id") or "通用"
    if kind == "board":
        return playbook.get("name") or "板块"
    if kind == "persona":
        return playbook.get("name") or "视角"
    return playbook.get("name") or "品种"
