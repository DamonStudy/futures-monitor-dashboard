"""Manual-refresh futures monitoring dashboard."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from tqsdk import TqApi, TqAuth

from .analysis import PeriodFrames, board_context, diagnose_contract
from .contract_specs import enrich_quote_with_specs, load_akshare_specs
from .contracts import all_contracts


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data"
CACHE_FILE = CACHE_DIR / "latest_snapshot.json"

app = Flask(__name__, static_folder=str(ROOT / "static"))


def load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/snapshot")
def snapshot():
    if not CACHE_FILE.exists():
        return jsonify({"ok": False, "message": "暂无缓存，请先刷新。", "items": []})
    data = read_cache()
    data["from_cache"] = True
    data["cache_is_today"] = cache_is_today(data)
    return jsonify(data)


@app.post("/api/refresh")
def refresh():
    try:
        force = request.args.get("force") == "1"
        cached = read_cache()
        if cached and cache_is_today(cached) and not force:
            cached["from_cache"] = True
            cached["cache_is_today"] = True
            return jsonify(cached)

        data = fetch_and_analyze()
        CACHE_DIR.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify(data)
    except Exception as exc:
        cached = None
        cached = read_cache()
        return jsonify(
            {
                "ok": False,
                "message": str(exc),
                "cached": cached,
                "items": cached.get("items", []) if cached else [],
                "boards": cached.get("boards", {}) if cached else {},
            }
        ), 500


def read_cache() -> dict[str, Any] | None:
    if not CACHE_FILE.exists():
        return None
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def cache_is_today(data: dict[str, Any]) -> bool:
    refreshed_at = data.get("refreshed_at")
    if not refreshed_at:
        return False
    try:
        return datetime.strptime(refreshed_at, "%Y-%m-%d %H:%M:%S").date() == datetime.now().date()
    except ValueError:
        return False


def fetch_and_analyze() -> dict[str, Any]:
    load_dotenv()
    account = os.getenv("TQ_ACCOUNT")
    password = os.getenv("TQ_PASSWORD")
    if not account or not password:
        raise RuntimeError("未找到 TQ_ACCOUNT/TQ_PASSWORD。请放入环境变量或本地 .env 文件。")

    api = TqApi(auth=TqAuth(account, password), web_gui=False, disable_print=True)
    try:
        contracts = all_contracts()
        specs = load_akshare_specs()
        requested: list[dict[str, Any]] = []
        for meta in contracts:
            symbol = meta["symbol"]
            requested.append(
                {
                    "meta": meta,
                    "quote": api.get_quote(symbol),
                    "day": api.get_kline_serial(symbol, 24 * 60 * 60, data_length=260),
                    "hour": api.get_kline_serial(symbol, 60 * 60, data_length=220),
                    "week": api.get_kline_serial(symbol, 7 * 24 * 60 * 60, data_length=140),
                }
            )

        deadline = time.time() + 30
        while time.time() < deadline:
            api.wait_update(deadline=time.time() + 1)
            if all(has_enough_rows(item["day"], 80) for item in requested):
                break

        first_pass = []
        errors = []
        for item in requested:
            try:
                quote = enrich_quote_with_specs(
                    item["meta"],
                    quote_to_dict(item["quote"]),
                    specs,
                )
                frames = PeriodFrames(
                    day=item["day"].copy(),
                    hour=item["hour"].copy(),
                    week=item["week"].copy(),
                )
                diag = diagnose_contract(item["meta"], frames, quote, {})
                if diag:
                    first_pass.append(diag)
            except Exception as exc:
                errors.append({"symbol": item["meta"]["symbol"], "message": str(exc)})

        boards = board_context(first_pass)
        final_items = []
        for diag in first_pass:
            context = {
                "same_direction_count": same_direction_count(first_pass, diag),
                "oi_change_pct": diag.get("metrics", {}).get("open_interest_change_pct"),
            }
            item = next(i for i in requested if i["meta"]["symbol"] == diag["symbol"])
            refined = diagnose_contract(
                item["meta"],
                PeriodFrames(item["day"].copy(), item["hour"].copy(), item["week"].copy()),
                enrich_quote_with_specs(item["meta"], quote_to_dict(item["quote"]), specs),
                context,
            )
            if refined:
                final_items.append(refined)

        final_items.sort(key=lambda row: row["score"], reverse=True)
        return {
            "ok": True,
            "mode": "manual_refresh",
            "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "universe_count": len(contracts),
            "active_count": len(final_items),
            "boards": boards,
            "items": final_items,
            "errors": errors[:20],
        }
    finally:
        api.close()


def has_enough_rows(df: pd.DataFrame, rows: int) -> bool:
    return len(df.dropna(subset=["close"])) >= rows if "close" in df else False


def quote_to_dict(quote: Any) -> dict[str, Any]:
    keys = (
        "instrument_id",
        "underlying_symbol",
        "last_price",
        "datetime",
        "instrument_name",
        "price_tick",
        "volume_multiple",
        "margin",
        "margin_rate",
        "long_margin_rate",
        "short_margin_rate",
        "margin_ratio",
        "long_margin_ratio",
        "short_margin_ratio",
    )
    data = {key: quote_value(quote, key) for key in keys}
    data["symbol"] = data.get("underlying_symbol") or data.get("instrument_id")
    return data


def quote_value(quote: Any, key: str) -> Any:
    if hasattr(quote, "get"):
        value = quote.get(key)
        if value is not None:
            return value
    return getattr(quote, key, None)


def same_direction_count(items: list[dict[str, Any]], target: dict[str, Any]) -> int:
    if target.get("direction") == "neutral":
        return 0
    return sum(
        1
        for item in items
        if item.get("board") == target.get("board") and item.get("direction") == target.get("direction")
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8010"))
    app.run(host="127.0.0.1", port=port, debug=False)
