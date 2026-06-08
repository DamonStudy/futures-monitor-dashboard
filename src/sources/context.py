"""Batch-level shared context for a refresh cycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..macro import build_macro_context


@dataclass
class BatchContext:
    """Shared facts fetched once per manual refresh."""

    macro: dict[str, Any]
    refreshed_at: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def macro_context(self) -> dict[str, Any]:
        return self.macro


def build_batch_context(*, calendar_days: int = 7) -> BatchContext:
    macro = build_macro_context(calendar_days=calendar_days)
    return BatchContext(
        macro=macro,
        refreshed_at=str(macro.get("refreshed_at") or ""),
        errors=list(macro.get("errors") or []),
    )
