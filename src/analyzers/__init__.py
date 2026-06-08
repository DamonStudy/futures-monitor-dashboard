"""Deterministic data analyzers — produce numbers, signals, and thresholds from market data."""

from __future__ import annotations

from typing import Any

import pandas as pd

from . import (
    basis,
    board_resonance,
    seasonality,
    candlestick_patterns,
    key_levels,
    macro_regime,
    position_rank,
    price_volume,
    technical_signals,
    term_structure,
    warehouse_receipts,
)
from .utils import signal_periods

ANALYZER_IDS = {
    "price_volume",
    "board_resonance",
    "seasonality",
    "technical_signals",
    "candlestick_patterns",
    "key_levels",
    "term_structure",
    "warehouse_receipts",
    "basis",
    "position_rank",
    "macro_regime",
}


def analyze_all(
    *,
    periods: dict[str, pd.DataFrame],
    chain_quotes: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    quote: dict[str, Any] | None = None,
    include_external: bool = True,
    macro_context: dict[str, Any] | None = None,
    direction: str = "neutral",
    board_peers: list[dict[str, Any]] | None = None,
    boards_summary: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    periods = signal_periods(periods)
    modules = [
        price_volume.analyze(periods),
        board_resonance.analyze(
            meta=meta or {},
            direction=direction,
            peers=board_peers,
            boards_summary=boards_summary,
        ),
        seasonality.analyze(meta=meta or {}, day=periods.get("day")),
        technical_signals.analyze(periods),
        candlestick_patterns.analyze(periods),
        key_levels.analyze(periods),
        term_structure.analyze(chain_quotes),
    ]
    if include_external:
        modules.append(warehouse_receipts.analyze(meta or {}))
        modules.append(basis.analyze(meta or {}, quote or {}))
        modules.append(position_rank.analyze(meta or {}, quote or {}))
    if macro_context:
        modules.append(macro_regime.analyze(macro_context))
    return modules
