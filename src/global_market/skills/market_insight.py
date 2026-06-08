"""Global market insight skill — composes phenomenon / mechanism / verify narrative."""

from __future__ import annotations

from typing import Any

from ...schemas.output import skill_result
from ..overview import build_narrative, format_change

SKILL_ID = "market_insight"
TITLE = "大盘解读"
PRIORITY = 70


def analyze(ctx: dict[str, Any], upstream_skills: list[dict[str, Any]]) -> dict[str, Any]:
    narrative = build_narrative(
        ctx.get("lead"),
        ctx.get("board_indices") or [],
        ctx.get("drivers") or [],
        ctx.get("macro"),
        board_stats=ctx.get("board_stats") or [],
    )
    phenomenon = _section_items(narrative, "phenomenon")
    mechanism = _section_items(narrative, "mechanism")
    verify = _section_items(narrative, "verify")

    _enrich_mechanism_from_board_stats(mechanism, ctx.get("board_stats") or [])
    _trim_sections(phenomenon, mechanism, verify)

    narrative = {
        "version": 2,
        "sections": [
            {"key": "phenomenon", "title": "现象", "items": phenomenon},
            {"key": "mechanism", "title": "机制", "items": mechanism},
            {"key": "verify", "title": "待验证", "items": verify},
        ],
    }

    core_hits = _core_hits_from_skills(upstream_skills)
    gaps = _gaps_from_context(ctx)
    headline = _headline(ctx, phenomenon)

    result = skill_result(
        SKILL_ID,
        TITLE,
        headline,
        priority=PRIORITY,
        signals=core_hits,
        notes=gaps,
    )
    result["narrative"] = narrative
    result["brief"] = {"headline": headline, "framework": [row.get("text", "") for row in mechanism[:3]]}
    result["core_hits"] = core_hits
    result["gaps"] = gaps
    result["judgment_note"] = _judgment_note(upstream_skills, gaps)
    return result


def _section_items(narrative: dict[str, Any], key: str) -> list[dict[str, str]]:
    for section in narrative.get("sections") or []:
        if section.get("key") == key:
            return list(section.get("items") or [])
    return []


def _enrich_mechanism_from_board_stats(
    mechanism: list[dict[str, str]],
    board_stats: list[dict[str, Any]],
) -> None:
    if not board_stats:
        return
    resonance = max(board_stats, key=lambda row: row.get("same_dir_ratio") or 0)
    if (resonance.get("same_dir_ratio") or 0) >= 0.65 and resonance.get("up", 0) >= 3:
        text = (
            f"{resonance.get('code')} 内部 {resonance.get('up')}/{resonance.get('product_count')} 品种偏多，"
            f"说明板块逻辑在品种层有共振，不只是指数层面的相对强弱"
        )
        if not any(item.get("label") == "品种共振" for item in mechanism):
            mechanism.append({"label": "品种共振", "text": text})

    divergent = max(
        board_stats,
        key=lambda row: abs(row.get("index_divergence") or 0),
    )
    div = divergent.get("index_divergence")
    if div is not None and abs(div) >= 1.2:
        text = (
            f"{divergent.get('code')} 指数周度{format_change(divergent.get('index_change_5d'))}，"
            f"品种中位数{format_change(divergent.get('median_change_5d'))}，"
            f"指数与成分节奏{'背离' if div < 0 else '领先'}"
        )
        if not any(item.get("label") == "指数背离" for item in mechanism):
            mechanism.append({"label": "指数背离", "text": text})


def _trim_sections(
    phenomenon: list[dict[str, str]],
    mechanism: list[dict[str, str]],
    verify: list[dict[str, str]],
) -> None:
    del phenomenon[4:]
    del mechanism[6:]
    del verify[4:]


def _core_hits_from_skills(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for skill in skills:
        if skill.get("id") == "market_insight":
            continue
        for sig in skill.get("signals") or []:
            hits.append(
                {
                    "name": f"{skill.get('title', '')} · {sig.get('name', '')}",
                    "text": sig.get("interpretation") or "",
                    "level": sig.get("level") or "info",
                }
            )
    return hits[:6]


def _gaps_from_context(ctx: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not ctx.get("contract_items"):
        gaps.append("尚未接入品种盯控缓存，板块内共振与梯队判断可能不完整")
    if (ctx.get("macro") or {}).get("status") == "unavailable":
        gaps.append("宏观发布数据缺失，机制段以核心变量为主")
    if len(ctx.get("board_stats") or []) < 3:
        gaps.append("部分南华板块缺少足够活跃品种，横截面样本偏少")
    return gaps[:3]


def _headline(ctx: dict[str, Any], phenomenon: list[dict[str, str]]) -> str:
    if phenomenon:
        return phenomenon[0].get("text") or "大盘解读"
    lead = ctx.get("lead") or {}
    weekly = (lead.get("changes") or {}).get("5d")
    return f"南华商品周度{format_change(weekly)}，详见现象/机制/待验证"


def _judgment_note(skills: list[dict[str, Any]], gaps: list[str]) -> str:
    ok = [skill for skill in skills if skill.get("status") != "unavailable" and skill.get("id") != "market_insight"]
    lead = f"已启用 {len(ok)} 个大盘 skill 生成解读"
    if gaps:
        return f"{lead}；{gaps[0]}"
    return f"{lead}；机制与待验证需随刷新数据持续核对"
