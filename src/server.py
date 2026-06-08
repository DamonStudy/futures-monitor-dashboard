"""Manual-refresh futures monitoring dashboard."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .global_market import build_global_overview
from .services import (
    cache_has_skills,
    cache_is_today,
    fetch_and_analyze,
    global_cache_reusable,
    global_schema_outdated,
    global_snapshot_should_persist,
    read_contract_snapshot,
    read_global_snapshot,
    read_json_cache,
    write_json_cache,
)


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data"
CACHE_FILE = CACHE_DIR / "latest_snapshot.json"
GLOBAL_CACHE_FILE = CACHE_DIR / "global_market_snapshot.json"

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
    data = read_contract_snapshot(CACHE_FILE)
    data["from_cache"] = True
    data["cache_is_today"] = cache_is_today(data)
    return jsonify(data)


@app.post("/api/refresh")
def refresh():
    try:
        load_dotenv()
        force = request.args.get("force") == "1"
        cached = read_contract_snapshot(CACHE_FILE)
        if cached and cache_is_today(cached) and cache_has_skills(cached) and not force:
            cached["from_cache"] = True
            cached["cache_is_today"] = True
            return jsonify(cached)

        data = fetch_and_analyze()
        write_json_cache(CACHE_FILE, data)
        return jsonify(data)
    except Exception as exc:
        cached = read_contract_snapshot(CACHE_FILE)
        return jsonify(
            {
                "ok": False,
                "message": str(exc),
                "cached": cached,
                "items": cached.get("items", []) if cached else [],
                "boards": cached.get("boards", {}) if cached else {},
            }
        ), 500


@app.get("/api/global-market")
def global_market_snapshot():
    load_dotenv()
    if not GLOBAL_CACHE_FILE.exists():
        return jsonify({"ok": False, "message": "暂无大盘首页缓存，请先刷新。"})
    raw = read_json_cache(GLOBAL_CACHE_FILE)
    contract = read_contract_snapshot(CACHE_FILE)
    data = read_global_snapshot(GLOBAL_CACHE_FILE, CACHE_FILE)
    if data and raw and global_snapshot_should_persist(raw, data, contract):
        write_json_cache(GLOBAL_CACHE_FILE, data)
    data["from_cache"] = True
    data["cache_is_today"] = cache_is_today(data)
    data["cache_has_nanhua"] = bool(data.get("nanhua_indices"))
    return jsonify(data)


@app.post("/api/global-market/refresh")
def global_market_refresh():
    try:
        load_dotenv()
        force = request.args.get("force") == "1"
        raw = read_json_cache(GLOBAL_CACHE_FILE) if GLOBAL_CACHE_FILE.exists() else None
        contract = read_contract_snapshot(CACHE_FILE)
        schema_outdated = global_schema_outdated(raw)
        cached = read_global_snapshot(GLOBAL_CACHE_FILE, CACHE_FILE)
        if cached and global_cache_reusable(cached, contract) and not force and not schema_outdated:
            if global_snapshot_should_persist(raw, cached, contract):
                write_json_cache(GLOBAL_CACHE_FILE, cached)
            cached["from_cache"] = True
            cached["cache_is_today"] = True
            cached["cache_has_nanhua"] = bool(cached.get("nanhua_indices"))
            return jsonify(cached)

        data = build_global_overview((contract or {}).get("items"))
        write_json_cache(GLOBAL_CACHE_FILE, data)
        data["from_cache"] = False
        data["cache_is_today"] = True
        data["cache_has_nanhua"] = bool(data.get("nanhua_indices"))
        return jsonify(data)
    except Exception as exc:
        cached = read_global_snapshot(GLOBAL_CACHE_FILE, CACHE_FILE)
        return jsonify(
            {
                "ok": False,
                "message": str(exc),
                "cached": cached,
                "lead": cached.get("lead") if cached else None,
                "nanhua_indices": cached.get("nanhua_indices", []) if cached else [],
                "drivers": cached.get("drivers", []) if cached else [],
                "macro": cached.get("macro") if cached else None,
            }
        ), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8010"))
    app.run(host="127.0.0.1", port=port, debug=False)
