"""Board resonance — whether same-board and related-board peers move together."""

from __future__ import annotations

from typing import Any

from ..domain.index_constituents import INDEX_CONSTITUENT_SPECS
from .schema import signal, module_result, table


DIRECTION_LABELS = {"up": "偏多", "down": "偏空", "neutral": "中性"}


def analyze(
    *,
    meta: dict[str, Any],
    direction: str,
    peers: list[dict[str, Any]] | None = None,
    boards_summary: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    board = meta.get("board") or "未分类"
    name = meta.get("name") or "-"
    peers = peers or []
    boards_summary = boards_summary or {}

    board_peers = [
        peer
        for peer in peers
        if peer.get("board") == board and peer.get("name") != name
    ]

    if not board_peers:
        return module_result(
            "board_resonance",
            "板块共振",
            f"{board}板块暂无其他活跃品种可对照。",
            status="unavailable",
            priority=40,
            notes=["板块共振基于当日刷新结果中同板块活跃品种的方向与涨跌幅。"],
        )

    same_dir = [peer for peer in board_peers if peer.get("direction") == direction]
    diff_dir = [
        peer
        for peer in board_peers
        if peer.get("direction") != direction
        and peer.get("direction") != "neutral"
        and direction != "neutral"
    ]
    neutral_dir = [peer for peer in board_peers if peer.get("direction") == "neutral"]

    total = len(board_peers)
    same_count = len(same_dir)
    ratio = same_count / total if total else 0.0
    label, priority, level = _classify_resonance(direction, same_count, total, ratio, len(diff_dir))

    peer_rows = [
        _peer_row(peer, direction)
        for peer in sorted(board_peers, key=lambda item: _peer_sort_key(item, direction))
    ]
    related_rows = _related_board_rows(board, direction, boards_summary)

    signals = _build_signals(label, direction, same_count, total, diff_dir, related_rows)
    tables = [
        table(
            "本板块品种对照",
            ["品种", "方向", "涨跌幅", "状态", "与本品种"],
            peer_rows[:10],
        )
    ]
    if related_rows:
        tables.append(
            table(
                "相关板块强弱",
                ["板块", "偏多", "偏空", "整体", "与本品种"],
                related_rows,
            )
        )

    summary = (
        f"{board}板块 {total} 个对照品种中，{same_count} 个同向（{DIRECTION_LABELS.get(direction, '中性')}），"
        f"判定为{label}。"
    )
    if related_rows:
        aligned = sum(1 for row in related_rows if row.get("与本品种") in ("同向", "偏同向"))
        summary += f" 相关板块 {len(related_rows)} 个中 {aligned} 个整体氛围同向。"

    return module_result(
        "board_resonance",
        "板块共振",
        summary,
        priority=priority,
        signals=signals,
        tables=tables,
        notes=["对照范围为本次刷新中的活跃品种，不含未入选品种。"],
    )


def related_boards(board: str) -> list[str]:
    related: set[str] = set()
    for spec in INDEX_CONSTITUENT_SPECS.values():
        boards = spec.get("boards") or []
        if board in boards:
            related.update(item for item in boards if item != board)
    return sorted(related)


def _classify_resonance(
    direction: str,
    same_count: int,
    total: int,
    ratio: float,
    diff_count: int,
) -> tuple[str, int, str]:
    if direction == "neutral":
        return "方向中性，共振参考价值有限", 42, "info"
    if total == 0:
        return "缺少对照样本", 40, "info"
    if same_count == total and total >= 2:
        return "板块强势共振", 78, "watch"
    if ratio >= 0.6 and same_count >= 2:
        return "板块共振偏强", 72, "watch"
    if diff_count >= 2 and same_count == 0:
        return "板块明显分化", 70, "watch"
    if diff_count >= 1 and ratio < 0.5:
        return "板块分化", 58, "info"
    if same_count >= 1:
        return "板块部分共振", 55, "info"
    return "板块暂未同向", 48, "info"


def _peer_row(peer: dict[str, Any], self_direction: str) -> dict[str, Any]:
    peer_dir = peer.get("direction") or "neutral"
    ret = peer.get("metrics", {}).get("return_pct")
    return {
        "品种": peer.get("name") or "-",
        "方向": DIRECTION_LABELS.get(peer_dir, "中性"),
        "涨跌幅": _fmt_pct(ret),
        "状态": _short_state(peer.get("state")),
        "与本品种": _alignment_label(self_direction, peer_dir),
    }


def _related_board_rows(
    board: str,
    direction: str,
    boards_summary: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for related in related_boards(board):
        info = boards_summary.get(related)
        if not info:
            continue
        tone = info.get("tone") or "分化"
        rows.append(
            {
                "板块": related,
                "偏多": info.get("up", 0),
                "偏空": info.get("down", 0),
                "整体": tone,
                "与本品种": _tone_alignment(direction, tone),
            }
        )
    return rows


def _build_signals(
    label: str,
    direction: str,
    same_count: int,
    total: int,
    diff_dir: list[dict[str, Any]],
    related_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = [
        signal(
            label,
            f"本板块 {same_count}/{total} 个品种与当前品种同向（{DIRECTION_LABELS.get(direction, '中性')}）。",
            level="watch" if "共振" in label and "部分" not in label else "info",
            value=f"{same_count}/{total}",
        )
    ]
    if diff_dir:
        names = "、".join(item.get("name") or "-" for item in diff_dir[:3])
        signals.append(
            signal(
                "板块内逆势品种",
                f"同板块中 {names} 等与当前方向不一致，需警惕产业链分化。",
                level="watch" if len(diff_dir) >= 2 else "info",
            )
        )
    aligned_related = [row for row in related_rows if row.get("与本品种") in ("同向", "偏同向")]
    if aligned_related:
        names = "、".join(row["板块"] for row in aligned_related[:3])
        signals.append(
            signal(
                "相关板块同向",
                f"{names} 等板块整体氛围与当前方向一致，有利于趋势延续判断。",
                level="info",
            )
        )
    headwind = [row for row in related_rows if row.get("与本品种") in ("逆向", "偏逆向")]
    if headwind:
        names = "、".join(row["板块"] for row in headwind[:3])
        signals.append(
            signal(
                "相关板块逆风",
                f"{names} 等板块整体氛围与当前方向相反，需降低单边置信度。",
                level="watch",
            )
        )
    return signals


def _alignment_label(self_direction: str, peer_direction: str) -> str:
    if self_direction == "neutral" or peer_direction == "neutral":
        return "中性"
    if self_direction == peer_direction:
        return "同向"
    return "逆向"


def _tone_alignment(direction: str, tone: str) -> str:
    if direction == "neutral":
        return "中性"
    if direction == "up":
        if tone == "偏强":
            return "同向"
        if tone == "偏弱":
            return "逆向"
        return "偏同向" if tone == "分化" else "中性"
    if direction == "down":
        if tone == "偏弱":
            return "同向"
        if tone == "偏强":
            return "逆向"
        return "偏逆向" if tone == "分化" else "中性"
    return "中性"


def _peer_sort_key(peer: dict[str, Any], self_direction: str) -> tuple[int, str]:
    alignment_rank = {"同向": 0, "中性": 1, "逆向": 2}
    label = _alignment_label(self_direction, peer.get("direction") or "neutral")
    return (alignment_rank.get(label, 9), peer.get("name") or "")


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "-"
        number = float(value)
        return f"{number:+.2f}%"
    except (TypeError, ValueError):
        return "-"


def _short_state(state: Any) -> str:
    text = str(state or "-")
    return text if len(text) <= 14 else f"{text[:13]}…"
