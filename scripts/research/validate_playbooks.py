#!/usr/bin/env python3
"""Validate research playbook YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.research.registry import list_playbooks, validate_all_playbooks  # noqa: E402


def main() -> int:
    catalog = list_playbooks()
    errors = validate_all_playbooks()
    print(f"layers: {len(catalog['layers'])}")
    print(f"products: {len(catalog['products'])}")
    print(f"boards: {len(catalog['boards'])}")
    print(f"personas: {len(catalog['personas'])}")
    if errors:
        print("validation errors:")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("all playbooks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
