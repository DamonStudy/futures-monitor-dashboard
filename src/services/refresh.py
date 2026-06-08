"""Batch refresh orchestration — TqSdk fetch + two-pass diagnosis."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import pandas as pd
from tqsdk import TqApi, TqAuth

from ..analysis import PeriodFrames, board_context, diagnose_contract
from ..contract_specs import enrich_quote_with_specs, load_akshare_specs
from ..contracts import all_contracts
from ..sources import build_batch_context
from ..sources.market import chain_is_ready, fetch_chain_quotes


def fetch_and_analyze() -> dict[str, Any]:
    account = os.getenv("TQ_ACCOUNT")
    password = os.getenv("TQ_PASSWORD")
    if not account or not password:
        raise RuntimeError("未找到 TQ_ACCOUNT/TQ_PASSWORD。请放入环境变量或本地 .env 文件。")
    enable_term_structure = os.getenv("ENABLE_TERM_STRUCTURE", "1") != "0"

    batch = build_batch_context()
    macro_context = batch.macro_context

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
                    "day": api.get_kline_serial(symbol, 24 * 60 * 60, data_length=1260),
                    "week": api.get_kline_serial(symbol, 7 * 24 * 60 * 60, data_length=140),
                    "chain": [],
                }
            )

        deadline = time.time() + 30
        while time.time() < deadline:
            api.wait_update(deadline=time.time() + 1)
            if all(has_enough_rows(item["day"], 80) for item in requested):
                break

        if enable_term_structure:
            for item in requested:
                item["chain"] = fetch_chain_quotes(api, item["meta"], main_quote=item["quote"])

            chain_deadline = time.time() + 12
            while time.time() < chain_deadline:
                pending = [item for item in requested if not chain_is_ready(item.get("chain"))]
                if not pending:
                    break
                api.wait_update(deadline=time.time() + 1)

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
                    week=item["week"].copy(),
                )
                diag = diagnose_contract(
                    item["meta"],
                    frames,
                    quote,
                    {"include_external_analyzers": False, "macro": macro_context},
                    chain_quotes=item.get("chain"),
                )
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
                "macro": macro_context,
                "board_peers": first_pass,
                "boards_summary": boards,
            }
            item = next(i for i in requested if i["meta"]["symbol"] == diag["symbol"])
            refined = diagnose_contract(
                item["meta"],
                PeriodFrames(item["day"].copy(), item["week"].copy()),
                enrich_quote_with_specs(item["meta"], quote_to_dict(item["quote"]), specs),
                context,
                chain_quotes=item.get("chain"),
            )
            if refined:
                final_items.append(refined)

        final_items.sort(key=lambda row: row["score"], reverse=True)
        return {
            "ok": True,
            "mode": "manual_refresh",
            "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "macro": macro_context,
            "universe_count": len(contracts),
            "active_count": len(final_items),
            "boards": boards,
            "items": final_items,
            "errors": errors[:20],
            "batch_errors": batch.errors,
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
