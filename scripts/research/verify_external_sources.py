#!/usr/bin/env python3
"""Smoke-test external data sources before integration. Read-only."""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable

import pandas as pd

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def recent_weekday(offset: int = 1) -> str:
    """YYYYMMDD for a recent weekday (default T-1)."""
    day = datetime.now().date() - timedelta(days=offset)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y%m%d")


def recent_weekday_iso(offset: int = 1) -> str:
    day = datetime.now().date() - timedelta(days=offset)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def run_case(
    priority: str,
    name: str,
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    started = time.perf_counter()
    row: dict[str, Any] = {
        "priority": priority,
        "name": name,
        "status": FAIL,
        "latency_ms": None,
        "summary": "",
        "details": {},
    }
    try:
        details = fn()
        row["status"] = details.pop("status", PASS)
        row["summary"] = details.pop("summary", "")
        row["details"] = details
    except Exception as exc:
        row["status"] = FAIL
        row["summary"] = f"{type(exc).__name__}: {exc}"
        row["details"] = {"traceback": traceback.format_exc(limit=3)}
    row["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return row


def test_basis() -> dict[str, Any]:
    import akshare as ak

    date = recent_weekday(1)
    df = ak.futures_spot_price(date)
    if df is None or df.empty:
        return {"status": FAIL, "summary": f"{date} 无返回"}

    cols = set(df.columns.astype(str))
    need = {"spot_price", "dom_basis", "dom_basis_rate", "dominant_contract"}
    missing = sorted(need - cols)
    if missing:
        return {"status": WARN, "summary": f"缺列 {missing}", "columns": list(cols)[:20]}

    sample = df[df["symbol"].astype(str).str.upper().isin(["RB", "CU", "I"])].head(3)
    latest_rows = sample.to_dict(orient="records") if len(sample) else df.head(3).to_dict(orient="records")
    non_null_basis = df["dom_basis"].notna().sum() if "dom_basis" in df.columns else 0
    return {
        "status": PASS if non_null_basis > 10 else WARN,
        "summary": f"{date} 共 {len(df)} 品种，有效 dom_basis {non_null_basis} 条",
        "date": date,
        "sample": latest_rows,
    }


def test_dce_position() -> dict[str, Any]:
    import akshare as ak

    date = recent_weekday(1)
    strategies = [
        ("futures_dce_position_rank", lambda: ak.futures_dce_position_rank(date=date)),
        ("futures_dce_position_rank_other", lambda: ak.futures_dce_position_rank_other(date=date)),
        ("get_dce_rank_table", lambda: ak.get_dce_rank_table(date=date)),
    ]
    results: dict[str, Any] = {}
    ok = 0
    for label, fn in strategies:
        try:
            out = fn()
            if isinstance(out, dict):
                keys = list(out.keys())[:5]
                size = sum(len(v) if hasattr(v, "__len__") else 1 for v in out.values())
                results[label] = {"type": "dict", "keys": keys, "size_hint": size}
                ok += 1 if size else 0
            elif isinstance(out, pd.DataFrame):
                results[label] = {"type": "df", "rows": len(out), "cols": list(out.columns)[:8]}
                ok += 1 if len(out) else 0
            else:
                results[label] = {"type": type(out).__name__, "repr": str(out)[:120]}
        except Exception as exc:
            results[label] = {"error": str(exc)}

    status = PASS if ok >= 1 else FAIL
    return {
        "status": status,
        "summary": f"{date} {ok}/{len(strategies)} 接口有数据",
        "date": date,
        "results": results,
    }


def test_inventory_em() -> dict[str, Any]:
    import akshare as ak

    samples = [("螺纹钢", "RB"), ("沪铜", "CU"), ("铁矿石", "I")]
    out: dict[str, Any] = {}
    ok = 0
    for cn, code in samples:
        df = ak.futures_inventory_em(symbol=cn)
        if df is None or df.empty:
            out[code] = {"rows": 0}
            continue
        df = df.copy()
        if "日期" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
            latest = str(df["日期"].max().date()) if df["日期"].notna().any() else None
        else:
            latest = None
        out[code] = {"rows": len(df), "latest": latest, "cols": list(df.columns)}
        ok += 1

    return {
        "status": PASS if ok >= 2 else WARN,
        "summary": f"{ok}/{len(samples)} 品种有东财库存(Em)数据",
        "samples": out,
    }


def test_inventory_99() -> dict[str, Any]:
    import akshare as ak

    if not hasattr(ak, "futures_inventory_99"):
        return {"status": SKIP, "summary": "当前 akshare 无 futures_inventory_99 接口"}

    samples = ["螺纹钢", "铜", "铁矿石"]
    out: dict[str, Any] = {}
    ok = 0
    for name in samples:
        try:
            df = ak.futures_inventory_99(symbol=name)
        except TypeError:
            df = ak.futures_inventory_99(name)
        except Exception as exc:
            out[name] = {"error": str(exc)}
            continue
        if df is None or df.empty:
            out[name] = {"rows": 0}
            continue
        out[name] = {"rows": len(df), "cols": list(df.columns)[:8]}
        ok += 1

    return {
        "status": PASS if ok >= 1 else WARN,
        "summary": f"{ok}/{len(samples)} 品种有 99期货库存 数据",
        "samples": out,
    }


def test_qhkc() -> dict[str, Any]:
    import akshare as ak

    probes = [
        ("qhkc_tool_foreign", {}),
        ("qhkc_tool_glass", {}),
    ]
    out: dict[str, Any] = {}
    ok = 0
    for func_name, kwargs in probes:
        if not hasattr(ak, func_name):
            out[func_name] = {"error": "not in akshare"}
            continue
        try:
            df = getattr(ak, func_name)(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                out[func_name] = {"rows": len(df), "cols": list(df.columns)[:6]}
                ok += 1
            else:
                out[func_name] = {"rows": 0}
        except Exception as exc:
            out[func_name] = {"error": str(exc)}

    status = PASS if ok else (WARN if any("error" in v for v in out.values()) else FAIL)
    return {
        "status": status,
        "summary": "奇货可查公开工具接口" + ("可用" if ok else "不可用或需 token"),
        "samples": out,
    }


def test_term_structure_history() -> dict[str, Any]:
    import akshare as ak

    end = recent_weekday(1)
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")
    daily = ak.get_futures_daily(start_date=start, end_date=end, market="SHFE")
    rb = daily[daily["symbol"].astype(str).str.upper().str.startswith("RB")] if daily is not None and not daily.empty else pd.DataFrame()
    main = ak.futures_main_sina(symbol="RB0", start_date=start, end_date=end)
    return {
        "status": PASS if len(rb) > 0 and main is not None and not main.empty else WARN,
        "summary": f"get_futures_daily RB {len(rb)} 行; futures_main_sina {0 if main is None else len(main)} 行",
        "range": [start, end],
        "main_cols": list(main.columns)[:8] if main is not None and not main.empty else [],
    }


def test_kline_fallback() -> dict[str, Any]:
    import akshare as ak

    end = recent_weekday_iso(1)
    start = recent_weekday_iso(8)
    results: dict[str, Any] = {}
    ok = 0

    try:
        df = ak.futures_hist_em(symbol="螺纹钢", period="daily")
        results["futures_hist_em"] = {"rows": len(df) if df is not None else 0}
        ok += bool(df is not None and len(df) > 10)
    except Exception as exc:
        results["futures_hist_em"] = {"error": str(exc)}

    try:
        df = ak.futures_zh_daily_sina(symbol="RB2510")
        results["futures_zh_daily_sina"] = {"rows": len(df) if df is not None else 0}
        ok += bool(df is not None and len(df) > 5)
    except Exception as exc:
        results["futures_zh_daily_sina"] = {"error": str(exc)}

    try:
        df = ak.futures_main_sina(symbol="RB0", start_date=start.replace("-", ""), end_date=end.replace("-", ""))
        results["futures_main_sina"] = {"rows": len(df) if df is not None else 0}
        ok += bool(df is not None and len(df) > 5)
    except Exception as exc:
        results["futures_main_sina"] = {"error": str(exc)}

    return {
        "status": PASS if ok >= 2 else WARN,
        "summary": f"{ok}/3 K线 fallback 可用",
        "results": results,
    }


def test_news_shmet() -> dict[str, Any]:
    import akshare as ak

    df = ak.futures_news_shmet(symbol="全部")
    if df is None or df.empty:
        return {"status": FAIL, "summary": "SHMET 返回空"}

    if "发布时间" in df.columns:
        df = df.copy()
        df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce")
        latest = df["发布时间"].max()
        age_days = (pd.Timestamp.now() - latest).days if pd.notna(latest) else None
    else:
        latest, age_days = None, None

    keywords = ["铜", "螺纹", "原油"]
    hits = {}
    if "内容" in df.columns:
        for kw in keywords:
            hits[kw] = int(df["内容"].astype(str).str.contains(kw, na=False).sum())

    status = PASS
    if age_days is not None and age_days > 3:
        status = WARN
    return {
        "status": status,
        "summary": f"共 {len(df)} 条，最新 {latest}，关键词命中 {hits}",
        "latest": str(latest) if latest is not None else None,
        "sample_titles": df.head(3).to_dict(orient="records") if len(df) else [],
    }


def test_sina_finance_search() -> dict[str, Any]:
    import re
    import requests

    keyword = "螺纹钢 期货"
    url = f"https://search.sina.com.cn/?q={keyword}&c=news&from=channel&col=finance&range=all&source=all&dedup=1&sort=time&page=1"
    r = requests.get(url, timeout=12)
    r.encoding = r.apparent_encoding or "utf-8"
    blocks = re.split(r']+class="[^"]*(?:box-result|result-mod)[^"]*"[^>]*>', r.text)[1:]
    titles = []
    for block in blocks[:5]:
        m = re.search(r']*href="([^"]+)"[^>]*>(.*?) ', block, flags=re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title:
                titles.append(title[:80])
    status = PASS if len(titles) >= 2 else WARN
    return {
        "status": status,
        "summary": f"新浪财经搜索命中 {len(titles)} 条标题",
        "sample_titles": titles,
        "http_status": r.status_code,
    }


def test_macro_info_ws() -> dict[str, Any]:
    import akshare as ak

    day = recent_weekday_iso(0)
    df = ak.macro_info_ws(date=day)
    if df is None:
        return {"status": WARN, "summary": f"{day} 返回 None"}
    return {
        "status": PASS if len(df) >= 0 else WARN,
        "summary": f"{day} 宏观日历 {len(df)} 条",
        "sample": df.head(3).to_dict(orient="records") if len(df) else [],
    }


def main() -> int:
    cases = [
        ("P0", "期现基差 futures_spot_price", test_basis),
        ("P1", "大商所持仓 DCE rank APIs", test_dce_position),
        ("P1", "东财库存 futures_inventory_em", test_inventory_em),
        ("P1", "99期货库存 futures_inventory_99", test_inventory_99),
        ("P2", "奇货可查 QHKC 工具接口", test_qhkc),
        ("P2", "历史期限结构 get_futures_daily / main_sina", test_term_structure_history),
        ("P2", "K线 fallback 多路", test_kline_fallback),
        ("NEWS", "SHMET 期货新闻 futures_news_shmet", test_news_shmet),
        ("NEWS", "新浪财经搜索 scrape", test_sina_finance_search),
        ("REF", "现有宏观日历 macro_info_ws", test_macro_info_ws),
    ]

    print(f"=== 数据源验证 {now_str()} ===\n")
    rows = []
    for priority, name, fn in cases:
        row = run_case(priority, name, fn)
        rows.append(row)
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}[row["status"]]
        print(f"{icon} [{row['priority']}] {row['name']}")
        print(f"   {row['summary']} ({row['latency_ms']} ms)")
        if row["status"] in (WARN, FAIL) and row.get("details"):
            detail_preview = json.dumps(row["details"], ensure_ascii=False, default=str)
            if len(detail_preview) > 400:
                detail_preview = detail_preview[:400] + "..."
            print(f"   detail: {detail_preview}")
        print()

    summary_path = "data/source_verification_latest.json"
    try:
        import os

        os.makedirs("data", exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({"checked_at": now_str(), "results": rows}, f, ensure_ascii=False, indent=2, default=str)
        print(f"完整结果已写入 {summary_path}")
    except OSError as exc:
        print(f"无法写入 {summary_path}: {exc}")

    failed = sum(1 for r in rows if r["status"] == FAIL)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
