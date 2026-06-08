"""Load and resolve research playbooks by layer, product, or board."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..symbol_parse import product_id_from_symbol  # re-export
from .schema import validate_playbook

PLAYBOOK_ROOT = Path(__file__).resolve().parent / "playbooks"
LAYER_DIR = PLAYBOOK_ROOT / "layers"
PRODUCT_DIR = PLAYBOOK_ROOT / "products"
BOARD_DIR = PLAYBOOK_ROOT / "boards"
PERSONA_DIR = PLAYBOOK_ROOT / "personas"

# Fixed order: macro → technical → board → product
LAYER_ORDER = ["macro", "technical"]


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict[str, Any]]:
    layers: dict[str, dict[str, Any]] = {}
    products: dict[str, dict[str, Any]] = {}
    boards: dict[str, dict[str, Any]] = {}
    personas: dict[str, dict[str, Any]] = {}

    if LAYER_DIR.is_dir():
        for path in sorted(LAYER_DIR.glob("*.yaml")):
            data = _read_yaml(path)
            if not data:
                continue
            layer_id = str(data.get("id") or path.stem)
            data["_kind"] = "layer"
            data["_path"] = str(path)
            layers[layer_id] = data

    if PRODUCT_DIR.is_dir():
        for path in sorted(PRODUCT_DIR.glob("*.yaml")):
            data = _read_yaml(path)
            if not data:
                continue
            product_id = str(data.get("id") or path.stem).lower()
            data["_kind"] = "product"
            data["_path"] = str(path)
            products[product_id] = data

    if BOARD_DIR.is_dir():
        for path in sorted(BOARD_DIR.glob("*.yaml")):
            data = _read_yaml(path)
            if not data:
                continue
            board_id = str(data.get("id") or path.stem)
            data["_kind"] = "board"
            data["_path"] = str(path)
            boards[board_id] = data

    if PERSONA_DIR.is_dir():
        for path in sorted(PERSONA_DIR.glob("*.yaml")):
            if path.stem.startswith("_"):
                continue
            data = _read_yaml(path)
            if not data:
                continue
            persona_id = str(data.get("id") or path.stem)
            data["_kind"] = "persona"
            data["_path"] = str(path)
            personas[persona_id] = data

    return {"layers": layers, "products": products, "boards": boards, "personas": personas}


def _read_yaml(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def get_playbook(*, symbol: str | None = None, board: str | None = None) -> dict[str, Any] | None:
    """Return the most specific single playbook (product > board). Kept for compatibility."""
    stack = resolve_playbook_stack(symbol=symbol, board=board)
    for playbook in reversed(stack):
        if playbook.get("_kind") in {"product", "board"}:
            return playbook
    return stack[-1] if stack else None


def resolve_playbook_stack(*, symbol: str | None = None, board: str | None = None) -> list[dict[str, Any]]:
    """Build the full knowledge stack: macro → technical → board → product."""
    catalog = _load_all()
    stack: list[dict[str, Any]] = []

    for layer_id in LAYER_ORDER:
        playbook = catalog["layers"].get(layer_id)
        if playbook:
            stack.append(playbook)

    product_id = product_id_from_symbol(symbol)
    if product_id and product_id in catalog["products"]:
        stack.append(catalog["products"][product_id])
    elif board and board in catalog["boards"]:
        stack.append(catalog["boards"][board])

    return stack


def get_layer_playbook(layer_id: str) -> dict[str, Any] | None:
    return _load_all()["layers"].get(layer_id)


def get_board_playbook(board: str | None) -> dict[str, Any] | None:
    if not board:
        return None
    return _load_all()["boards"].get(board)


def get_product_playbook(symbol: str | None) -> dict[str, Any] | None:
    product_id = product_id_from_symbol(symbol)
    if not product_id:
        return None
    return _load_all()["products"].get(product_id)


def resolve_personas(*, symbol: str | None = None, board: str | None = None) -> list[dict[str, Any]]:
    """Return persona playbooks matching product or board scope."""
    catalog = _load_all()
    product_id = product_id_from_symbol(symbol)
    matched: list[dict[str, Any]] = []
    for persona in catalog["personas"].values():
        scope = persona.get("scope") or {}
        if scope.get("all_commodities"):
            matched.append(persona)
            continue
        products = [str(item).lower() for item in scope.get("products") or []]
        boards = [str(item) for item in scope.get("boards") or []]
        if product_id and product_id in products:
            matched.append(persona)
        elif board and board in boards:
            matched.append(persona)
    return matched


def list_playbooks() -> dict[str, list[str]]:
    catalog = _load_all()
    return {
        "layers": sorted(catalog["layers"]),
        "products": sorted(catalog["products"]),
        "boards": sorted(catalog["boards"]),
        "personas": sorted(catalog["personas"]),
    }


def validate_all_playbooks() -> list[str]:
    """Validate every playbook file; return human-readable errors."""
    catalog = _load_all()
    errors: list[str] = []
    for layer_id, data in catalog["layers"].items():
        for message in validate_playbook(data, kind="layer"):
            errors.append(f"layers/{layer_id}.yaml: {message}")
    for product_id, data in catalog["products"].items():
        for message in validate_playbook(data, kind="product"):
            errors.append(f"products/{product_id}.yaml: {message}")
    for board_id, data in catalog["boards"].items():
        for message in validate_playbook(data, kind="board"):
            errors.append(f"boards/{board_id}.yaml: {message}")
    for persona_id, data in catalog["personas"].items():
        for message in validate_playbook(data, kind="persona"):
            errors.append(f"personas/{persona_id}.yaml: {message}")
    return errors
