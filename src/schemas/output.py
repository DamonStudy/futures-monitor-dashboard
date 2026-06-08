"""Shared structured output helpers."""

from __future__ import annotations

from typing import Any


def module_result(
    module_id: str,
    title: str,
    summary: str,
    *,
    priority: int = 50,
    status: str = "ok",
    signals: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
    levels: list[dict[str, Any]] | None = None,
    charts: list[dict[str, Any]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "analyzer",
        "id": module_id,
        "title": title,
        "summary": summary,
        "priority": max(0, min(int(priority), 100)),
        "status": status,
        "signals": signals or [],
        "tables": tables or [],
        "levels": levels or [],
        "charts": charts or [],
        "notes": notes or [],
    }


def skill_result(
    skill_id: str,
    title: str,
    summary: str,
    *,
    priority: int = 50,
    status: str = "ok",
    signals: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
    levels: list[dict[str, Any]] | None = None,
    charts: list[dict[str, Any]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "skill",
        "id": skill_id,
        "title": title,
        "summary": summary,
        "priority": max(0, min(int(priority), 100)),
        "status": status,
        "signals": signals or [],
        "tables": tables or [],
        "levels": levels or [],
        "charts": charts or [],
        "notes": notes or [],
    }


def signal(
    name: str,
    interpretation: str,
    *,
    level: str = "info",
    period: str | None = None,
    value: Any = None,
    threshold: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "level": level,
        "period": period,
        "value": value,
        "threshold": threshold,
        "interpretation": interpretation,
    }


def table(title: str, columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": title, "columns": columns, "rows": rows}
