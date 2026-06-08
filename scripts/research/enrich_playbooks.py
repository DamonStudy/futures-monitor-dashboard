#!/usr/bin/env python3
"""Enrich persona catalogs with distill metadata; validate coverage."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = ROOT / "src/research/playbooks"
CATALOGS = PLAYBOOKS / "catalogs"
PERSONAS = PLAYBOOKS / "personas"

# Heuristic: map citic report filename hints → distilled step ids
CITIC_STEP_HINTS: list[tuple[str, str]] = [
    ("宏观", "citic_macro_liquidity_regime"),
    ("非农", "citic_macro_fed_path"),
    ("美国经济", "citic_macro_fed_path"),
    ("议息", "citic_macro_fed_path"),
    ("黑色金属", "citic_black_supply_demand_table"),
    ("黑色建材", "citic_black_supply_demand_table"),
    ("铁矿", "citic_i_inventory_short_rally"),
    ("玻璃纯碱", "citic_black_glass_sa_chain"),
    ("PX", "citic_energy_px_polyester"),
    ("PTA", "citic_energy_px_polyester"),
    ("甲醇", "citic_energy_methanol_framework"),
    ("伊朗", "citic_event_methanol_iran"),
    ("尿素", "citic_agri_ur_demand"),
    ("油脂", "citic_agri_oils_meals"),
    ("贵金属", "citic_precious_liquidity"),
    ("黄金", "citic_precious_liquidity"),
    ("基本金属", "citic_metals_financial_property"),
    ("新能源金属", "citic_newenergy_lc_si"),
    ("碳酸锂", "citic_newenergy_lc_si"),
    ("镍", "citic_ni_indonesia_policy"),
    ("原油", "citic_energy_oil_products"),
    ("套利", "citic_arbitrage_cross_border"),
    ("周度综述", "citic_cross_asset_rotation"),
]


def guess_citic_steps(filename: str) -> list[str]:
    matched: list[str] = []
    for hint, step_id in CITIC_STEP_HINTS:
        if hint in filename and step_id not in matched:
            matched.append(step_id)
    return matched or ["citic_cross_asset_rotation"]


def enrich_citic_catalog() -> None:
    path = CATALOGS / "citic.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed_dir = ROOT / data["parsed_folder"]
    for entry in data.get("reports") or []:
        file_name = entry["file"]
        stem = Path(file_name).stem
        md = parsed_dir / f"{stem}.md"
        if "parsed_ok" not in entry:
            entry["parsed_ok"] = md.exists() and md.stat().st_size > 100
        if "report_date" not in entry:
            m = re.match(r"^(\d{8})", file_name) or re.search(r"(\d{8})", file_name)
            if m:
                d = m.group(1)
                entry["report_date"] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        entry.setdefault("data_policy", "mind_only")
        entry.setdefault("knowledge_type", "checklist")
        entry.setdefault("freshness", "semi_annual")
        steps = guess_citic_steps(file_name)
        entry["distilled_to"] = steps
        entry["distill_status"] = "done" if entry.get("parsed_ok") else "pending"
    data["stats"] = {
        "reports": len(data["reports"]),
        "parsed_ok": sum(1 for r in data["reports"] if r.get("parsed_ok")),
        "parsed_pending": sum(1 for r in data["reports"] if not r.get("parsed_ok")),
        "distill_done": sum(1 for r in data["reports"] if r.get("distill_status") == "done"),
    }
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"updated {path}")


def build_peifengke_catalog() -> None:
    source = ROOT / "期货原始资料" / "培风客-铜"
    files = sorted(source.glob("*"))
    reports = []
    for f in files:
        if f.suffix.lower() not in {".docx", ".doc", ".pdf", ".md"}:
            continue
        m = re.match(r"^(\d{8})", f.stem.replace(" ", ""))
        date = None
        if m:
            d = m.group(1)
            date = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        reports.append(
            {
                "file": f.name,
                "report_date": date,
                "parsed_ok": False,
                "chain": "product",
                "tags": ["铜", "培风客"],
                "products": ["cu"],
                "knowledge_type": "framework",
                "data_policy": "mind_only",
                "freshness": "evergreen",
                "distill_status": "done",
                "distilled_to": [
                    "time_horizon",
                    "structural_cyclical",
                    "long_supply_demand",
                    "medium_industrial",
                    "macro_quadrant",
                    "trade_inventory",
                    "market_participants",
                ],
            }
        )
    catalog = {
        "id": "peifengke_cu_catalog",
        "author": "培风客",
        "persona": "peifengke_cu",
        "updated": "2026-06-08",
        "source_folder": "期货原始资料/培风客-铜",
        "parsed_folder": "data/research/parsed/peifengke-cu",
        "stats": {
            "reports": len(reports),
            "parsed_ok": 0,
            "distill_done": len(reports),
        },
        "reports": reports,
    }
    out = CATALOGS / "peifengke_cu.yaml"
    out.write_text(yaml.dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"wrote {out} ({len(reports)} reports)")


def build_macro_brokers_catalog() -> None:
    source = ROOT / "期货原始资料" / "期货宏观"
    reports = []
    for f in sorted(source.glob("*.pdf")):
        broker = "未知"
        m = re.match(r"^\d{8}-([^-]+)-", f.name)
        if m:
            broker = m.group(1)
        reports.append(
            {
                "file": f.name,
                "report_date": f.name[:8] if f.name[:8].isdigit() else None,
                "parsed_ok": (ROOT / "data/research/parsed/macro" / f"{f.stem}.md").exists(),
                "chain": "macro",
                "tags": ["宏观", broker],
                "knowledge_type": "framework",
                "data_policy": "mind_only",
                "freshness": "semi_annual",
                "distill_status": "indexed",
                "note": "已并入 layers/macro.yaml 通用方法论；券商立场待拆 macro persona，不存观点与数字",
                "distilled_to": [
                    "regime",
                    "monetary_path",
                    "oil_geopolitics",
                    "cross_asset",
                    "commodity_filter",
                ],
            }
        )
    catalog = {
        "id": "macro_brokers_catalog",
        "author": "多券商宏观合集",
        "persona": None,
        "updated": "2026-06-08",
        "source_folder": "期货原始资料/期货宏观",
        "parsed_folder": "data/research/parsed/macro",
        "stats": {"reports": len(reports), "distill_status": "indexed_only"},
        "reports": reports,
    }
    out = CATALOGS / "macro_brokers.yaml"
    out.write_text(yaml.dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"wrote {out} ({len(reports)} reports)")


def main() -> int:
    build_peifengke_catalog()
    build_macro_brokers_catalog()
    enrich_citic_catalog()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
