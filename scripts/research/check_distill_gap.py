#!/usr/bin/env python3
"""List catalog reports that are parsed but not distilled, or not parsed."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / "src/research/playbooks/catalogs"


def check_catalog(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    print(f"\n== {path.name} ({data.get('author', '')}) ==")
    pending_parse = []
    pending_distill = []
    for entry in data.get("reports") or []:
        if not entry.get("parsed_ok"):
            pending_parse.append(entry["file"])
        elif entry.get("distill_status") not in {"done", "indexed"}:
            pending_distill.append(entry["file"])
    print(f"  reports: {len(data.get('reports') or [])}")
    print(f"  pending parse: {len(pending_parse)}")
    print(f"  pending distill: {len(pending_distill)}")
    for name in pending_parse[:8]:
        print(f"    [parse] {name}")
    if len(pending_parse) > 8:
        print(f"    ... +{len(pending_parse) - 8} more")
    for name in pending_distill[:5]:
        print(f"    [distill] {name}")


def main() -> int:
    for path in sorted(CATALOGS.glob("*.yaml")):
        if path.stem.startswith("_"):
            continue
        check_catalog(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
