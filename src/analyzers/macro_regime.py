"""Macro regime analyzer — rates, releases, and economic calendar."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .schema import module_result, signal, table

SKILL_ID = "macro_regime"
TITLE = "宏观环境"
PRIORITY = 43


def analyze(macro_context: dict[str, Any] | None) -> dict[str, Any]:
    if not macro_context or macro_context.get("status") == "unavailable":
        return module_result(
            SKILL_ID,
            TITLE,
            "宏观数据暂不可用。",
            status="unavailable",
            priority=PRIORITY - 10,
        )

    snapshot = macro_context.get("snapshot") or {}
    calendar = macro_context.get("calendar") or {}
    drivers = {row["id"]: row for row in snapshot.get("drivers") or [] if row.get("id")}
    signals: list[dict[str, Any]] = []
    notes: list[str] = []

    us10y = drivers.get("us10y")
    if us10y:
        change_20d = (us10y.get("changes") or {}).get("20d")
        level = us10y.get("value_label") or us10y.get("latest_value")
        tone = _rate_tone(change_20d)
        signals.append(
            signal(
                "美国10年期国债收益率",
                f"最新 {level}，近20日 {_format_bp(change_20d)}；{tone}",
                level="watch" if abs(change_20d or 0) >= 15 else "info",
                value=us10y.get("latest_value"),
                threshold="20日变化",
            )
        )

    usdcny = drivers.get("usdcny_fixing")
    if usdcny:
        change_20d = (usdcny.get("changes") or {}).get("20d")
        signals.append(
            signal(
                "美元兑人民币中间价",
                f"最新 {usdcny.get('value_label') or usdcny.get('latest_value')}，近20日 {_format_pct(change_20d)}",
                level="info",
                value=usdcny.get("latest_value"),
            )
        )

    for release in snapshot.get("releases") or []:
        if release.get("pending"):
            signals.append(
                signal(
                    release["title"],
                    f"待公布（前值 {release.get('previous')} {release.get('unit', '')}）",
                    level="watch",
                )
            )
            continue
        actual = release.get("actual")
        forecast = release.get("forecast")
        if actual is None:
            continue
        body = f"公布 {actual}{release.get('unit', '')}"
        if forecast is not None:
            body += f"，预期 {forecast}"
        if release.get("previous") is not None:
            body += f"，前值 {release['previous']}"
        level = "critical" if forecast is not None and actual != forecast else "info"
        signals.append(signal(release["title"], body, level=level, value=actual, threshold=str(forecast) if forecast else None))

    next_event = calendar.get("next_event")
    if next_event:
        delta = _days_until(next_event.get("datetime"))
        when = "今日" if delta == 0 else f"{delta} 天后" if delta else "即将"
        signals.append(
            signal(
                "宏观日历",
                f"{when} · {next_event.get('region')} · {next_event.get('title')}",
                level="watch" if delta is not None and delta <= 2 else "info",
            )
        )

    if calendar.get("risk_window_48h"):
        notes.append("未来 48 小时内有高重要性宏观事件，注意波动窗口。")

    upcoming = calendar.get("upcoming") or []
    summary_parts = []
    if us10y:
        summary_parts.append(f"10Y {us10y.get('value_label') or us10y.get('latest_value')}")
    if next_event:
        summary_parts.append(f"下一事件：{next_event.get('title')}")
    summary = "；".join(summary_parts) if summary_parts else "宏观快照已更新"

    result = module_result(
        SKILL_ID,
        TITLE,
        summary,
        priority=PRIORITY,
        signals=signals[:12],
        notes=notes,
        tables=[_calendar_table(upcoming)] if upcoming else [],
    )
    result["macro_refreshed_at"] = macro_context.get("refreshed_at")
    result["risk_window_48h"] = bool(calendar.get("risk_window_48h"))
    return result


def _calendar_table(events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for event in events[:12]:
        rows.append(
            {
                "时间": f"{event.get('date')} {event.get('time')}",
                "地区": event.get("region"),
                "事件": event.get("title"),
                "重要性": event.get("importance"),
            }
        )
    return table("未来宏观事件", ["时间", "地区", "事件", "重要性"], rows)


def _rate_tone(change_bp: float | None) -> str:
    if change_bp is None:
        return "利率环境待观察"
    if change_bp >= 20:
        return "利率上行，商品估值通常承压"
    if change_bp <= -20:
        return "利率回落，风险偏好通常改善"
    return "利率变动温和"


def _format_bp(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.1f}bp"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def _days_until(value: Any) -> int | None:
    if not value:
        return None
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    elif isinstance(value, datetime):
        dt = value
    else:
        return None
    return max(0, (dt.date() - date.today()).days)
