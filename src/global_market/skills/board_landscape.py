"""Global board landscape skill — weekly sector structure from indices + contract aggregates."""

from __future__ import annotations

from typing import Any

from ...schemas.output import signal, skill_result
from ..overview import format_change, _short_index_name, _weekly_board_scores, _weekly_tone_label

SKILL_ID = "board_landscape"
TITLE = "板块结构"
PRIORITY = 55


def analyze(ctx: dict[str, Any]) -> dict[str, Any]:
    lead = ctx.get("lead")
    board_indices = ctx.get("board_indices") or []
    board_stats = ctx.get("board_stats") or []

    if not board_indices and not board_stats:
        return skill_result(
            SKILL_ID,
            TITLE,
            "暂无板块指数或品种聚合数据。",
            status="unavailable",
            priority=20,
        )

    signals: list[dict[str, Any]] = []
    scored = _weekly_board_scores(board_indices)

    if lead:
        weekly = (lead.get("changes") or {}).get("5d")
        ytd = (lead.get("changes") or {}).get("ytd")
        text = f"{lead.get('name')}周度{format_change(weekly)}，{_weekly_tone_label(weekly)}"
        if ytd is not None and weekly is not None and ytd > 5 and weekly < -0.5:
            text += "；年内仍强但周度回调，更像休整"
        signals.append(signal("商品总指数", text, level=_level_from_weekly(weekly), period="5d", value=weekly))

    if scored:
        up = sum(1 for _, change in scored if change > 0)
        down = sum(1 for _, change in scored if change < 0)
        signals.append(
            signal(
                "板块广度",
                f"周度 {down} 跌 / {up} 涨，{'整体偏防守' if down > up else '整体偏暖' if up > down else '涨跌互现'}",
                level="watch" if abs(down - up) >= 2 else "info",
            )
        )
        strongest_row, strongest_chg = max(scored, key=lambda pair: pair[1])
        weakest_row, weakest_chg = min(scored, key=lambda pair: pair[1])
        signals.append(
            signal(
                "指数轮动",
                f"{_short_index_name(strongest_row.get('name', ''))}({format_change(strongest_chg)})最强，"
                f"{_short_index_name(weakest_row.get('name', ''))}({format_change(weakest_chg)})最弱",
                level="info",
            )
        )

    for stat in _top_divergence_boards(board_stats):
        div = stat.get("index_divergence")
        if div is None:
            continue
        top = stat.get("top_product") or {}
        signals.append(
            signal(
                f"{stat.get('code')}内部分化",
                f"板块指数周度{format_change(stat.get('index_change_5d'))}，"
                f"品种中位数{format_change(stat.get('median_change_5d'))}，"
                f"领涨{top.get('name')}({format_change(top.get('change_5d'))})",
                level="watch" if abs(div) >= 1.5 else "info",
            )
        )

    for stat in _top_resonance_boards(board_stats):
        signals.append(
            signal(
                f"{stat.get('code')}共振",
                f"{stat.get('product_count')} 个品种中 {stat.get('up')} 偏多 / {stat.get('down')} 偏空，"
                f"{'同向性较强' if stat.get('same_dir_ratio', 0) >= 0.6 else '内部分歧'}",
                level="watch" if stat.get("same_dir_ratio", 0) >= 0.65 else "info",
            )
        )

    summary = _landscape_summary(scored, board_stats)
    return skill_result(
        SKILL_ID,
        TITLE,
        summary,
        priority=PRIORITY,
        signals=signals,
        notes=["大盘板块 skill：南华指数 + 品种横截面聚合，不调用 board_resonance 数据模块。"],
    )


def _top_divergence_boards(board_stats: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    rows = [row for row in board_stats if row.get("index_divergence") is not None]
    rows.sort(key=lambda row: abs(row.get("index_divergence") or 0), reverse=True)
    return rows[:limit]


def _top_resonance_boards(board_stats: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    rows = [row for row in board_stats if (row.get("product_count") or 0) >= 3]
    rows.sort(key=lambda row: row.get("same_dir_ratio") or 0, reverse=True)
    return rows[:limit]


def _landscape_summary(scored: list, board_stats: list[dict[str, Any]]) -> str:
    if scored:
        down = sum(1 for _, change in scored if change < 0)
        up = sum(1 for _, change in scored if change > 0)
        if down > up:
            return "周度板块面偏冷，优先找相对强势链条而非全面做多"
    if board_stats:
        strong = max(board_stats, key=lambda row: row.get("same_dir_ratio") or 0)
        if (strong.get("same_dir_ratio") or 0) >= 0.65:
            return f"{strong.get('code')} 内部共振偏强，适合沿板块内部梯队跟踪"
    return "板块分化为主，宜结构性配置"


def _level_from_weekly(change: float | None) -> str:
    if change is None:
        return "info"
    if change <= -1.5 or change >= 1.5:
        return "watch"
    return "info"
