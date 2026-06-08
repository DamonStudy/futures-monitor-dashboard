"""Playbook structure validation for research reasoning chains."""

from __future__ import annotations

from typing import Any

REQUIRED_PRODUCT_KEYS = {"id", "name", "board", "reasoning_chain"}
REQUIRED_BOARD_KEYS = {"id", "name", "reasoning_chain"}
REQUIRED_LAYER_KEYS = {"id", "name", "reasoning_chain"}
REQUIRED_PERSONA_KEYS = {"id", "name", "reasoning_chain"}
REQUIRED_STEP_KEYS = {"id", "title"}

CHAIN_TYPES = {
    "macro",
    "cross_asset",
    "board",
    "product",
    "strategy",
    "event",
    "arbitrage",
    "technical",
}
KNOWLEDGE_TYPES = {"framework", "checklist", "variable", "causal", "seasonal", "risk"}
DATA_POLICIES = {"no_numbers", "mind_only", "reference_structure", "live_link"}
FRESHNESS_LEVELS = {"evergreen", "semi_annual", "event", "deprecated"}


def validate_playbook(data: dict[str, Any], *, kind: str = "product") -> list[str]:
    """Return a list of validation errors; empty means valid."""
    errors: list[str] = []
    if kind == "product":
        required = REQUIRED_PRODUCT_KEYS
    elif kind == "layer":
        required = REQUIRED_LAYER_KEYS
    elif kind == "persona":
        required = REQUIRED_PERSONA_KEYS
    else:
        required = REQUIRED_BOARD_KEYS
    missing = required - set(data)
    if missing:
        errors.append(f"missing keys: {', '.join(sorted(missing))}")

    chain = data.get("reasoning_chain")
    if not isinstance(chain, list) or not chain:
        errors.append("reasoning_chain must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, step in enumerate(chain):
        if not isinstance(step, dict):
            errors.append(f"reasoning_chain[{index}] must be an object")
            continue
        step_missing = REQUIRED_STEP_KEYS - set(step)
        if step_missing:
            errors.append(f"step[{index}] missing: {', '.join(sorted(step_missing))}")
        step_id = step.get("id")
        if isinstance(step_id, str):
            if step_id in seen_ids:
                errors.append(f"duplicate step id: {step_id}")
            seen_ids.add(step_id)
        for label, value, allowed in (
            ("chain", step.get("chain"), CHAIN_TYPES),
            ("knowledge_type", step.get("knowledge_type"), KNOWLEDGE_TYPES),
            ("data_policy", step.get("data_policy"), DATA_POLICIES),
            ("freshness", step.get("freshness"), FRESHNESS_LEVELS),
        ):
            if value is not None and value not in allowed:
                errors.append(f"step[{index}] invalid {label}: {value}")

    for key in ("confirmation", "invalidation", "seasonal_notes", "risk_factors", "sources"):
        value = data.get(key)
        if value is not None and not isinstance(value, list):
            errors.append(f"{key} must be a list when present")

    return errors
