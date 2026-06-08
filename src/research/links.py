"""Resolve analyzer links on playbook steps (supports legacy skill_links)."""

from __future__ import annotations

from typing import Any


def step_analyzer_links(step: dict[str, Any]) -> list[str]:
    links = step.get("analyzer_links")
    if links:
        return list(links)
    legacy = step.get("skill_links")
    return list(legacy) if legacy else []
