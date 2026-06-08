"""Aggregate skill outputs into a compact dashboard brief."""

from __future__ import annotations

from typing import Any

from .schema import signal, skill_result


def analyze(
    *,
    state: str,
    level: str,
    direction: str,
    score: int,
    skills: list[dict[str, Any]],
) -> dict[str, Any]:
    data_skills = [skill for skill in skills if skill.get("id") not in {"summary", "research_lens"}]
    research = next((skill for skill in skills if skill.get("id") == "research_lens"), None)

    strongest = sorted(
        (sig | {"skill": skill["title"]} for skill in data_skills for sig in skill.get("signals", [])),
        key=lambda item: _level_weight(item.get("level")),
        reverse=True,
    )[:5]

    direction_text = {"up": "偏多", "down": "偏空", "neutral": "中性"}.get(direction, "中性")
    triggers = [f"{item['skill']} · {item['name']}" for item in strongest[:3]]

    narrative = (research or {}).get("brief") or (research or {}).get("narrative")
    if isinstance(narrative, dict):
        brief = {
            "headline": narrative.get("headline") or f"{state} · {level} · 方向{direction_text} · 关注分{score}",
            "triggers": triggers,
            "evidence": narrative.get("evidence") or [],
            "framework": narrative.get("framework") or [],
            "verify": narrative.get("verify") or [],
        }
    else:
        brief = {
            "headline": f"{state} · {level} · 方向{direction_text} · 关注分{score}",
            "triggers": triggers,
            "evidence": [],
            "framework": [],
            "verify": [],
        }

    result = skill_result(
        "summary",
        "综合提炼",
        brief["headline"],
        priority=score,
        signals=[
            signal(
                item["name"],
                item["interpretation"],
                level=item.get("level", "info"),
                period=item.get("period"),
                value=item.get("value"),
                threshold=item.get("threshold"),
            )
            for item in strongest
        ],
    )
    result["brief"] = brief
    return result


def _level_weight(level: str | None) -> int:
    return {"critical": 4, "watch": 3, "info": 2}.get(level or "info", 1)
