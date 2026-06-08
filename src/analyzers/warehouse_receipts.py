"""Warehouse receipt diagnostics from public Eastmoney inventory data."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd
import requests

from .schema import signal, module_result, table
from .utils import clean_number, fmt_number, parse_product_symbol, pct_text


EASTMONEY_INVENTORY_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
LOWERCASE_CODES = {"bc", "lc", "lu", "nr", "pd", "ps", "pt", "sc", "si"}


def analyze(meta: dict[str, Any]) -> dict[str, Any]:
    product_code = inventory_code(meta.get("symbol"))
    if not product_code:
        return unavailable("仓单库存", "无法识别品种代码。")

    try:
        data = fetch_inventory(product_code)
    except Exception as exc:
        return unavailable("仓单库存", f"仓单数据请求失败：{exc}")

    if len(data) == 0:
        return unavailable("仓单库存", "该品种暂无公开仓单库存数据。")

    latest = data.iloc[-1]
    latest_stock = clean_number(latest.get("库存"), 0)
    latest_date = str(latest.get("日期"))
    percentile = percentile_rank(data["库存"], latest_stock)
    changes = {days: change_row(data, days) for days in (1, 5, 20, 60)}
    streak = consecutive_change_days(data)
    signals = build_signals(changes, percentile, streak)
    priority = max([45] + [_signal_priority(item) for item in signals])

    summary = (
        f"{latest_date}仓单库存{fmt_number(latest_stock, 0)}，"
        f"较前一日{signed_number(changes[1]['change'])}，"
        f"近20日{signed_number(changes[20]['change'])}，"
        f"处于近{len(data)}个样本{ratio_text(percentile)}。"
    )

    notes = [
        "该口径来自公开期货库存/仓单数据，适合观察近1-3个月变化，不等同于产业社会库存。",
    ]
    if streak:
        direction = "增加" if streak > 0 else "减少"
        notes.append(f"仓单已连续{abs(streak)}个交易日{direction}。")

    return module_result(
        "warehouse_receipts",
        "仓单库存",
        summary,
        priority=priority,
        signals=signals,
        tables=[
            table(
                "仓单变化",
                ["窗口", "基准库存", "最新库存", "变化", "变化率"],
                [
                    {
                        "窗口": f"{days}日",
                        "基准库存": fmt_number(row["base"], 0),
                        "最新库存": fmt_number(latest_stock, 0),
                        "变化": signed_number(row["change"]),
                        "变化率": ratio_text(row["pct"]),
                    }
                    for days, row in changes.items()
                ],
            )
        ],
        notes=notes,
    )


def inventory_code(symbol: str | None) -> str | None:
    _, product = parse_product_symbol(symbol)
    if not product:
        return None
    product = product.strip()
    return product if product in LOWERCASE_CODES else product.upper()


@lru_cache(maxsize=128)
def fetch_inventory(product_code: str) -> pd.DataFrame:
    params = {
        "reportName": "RPT_FUTU_STOCKDATA",
        "columns": "SECURITY_CODE,TRADE_DATE,ON_WARRANT_NUM,ADDCHANGE",
        "filter": f"""(SECURITY_CODE="{product_code}")(TRADE_DATE>='2020-10-28')""",
        "pageNumber": "1",
        "pageSize": "500",
        "sortTypes": "-1",
        "sortColumns": "TRADE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    response = requests.get(EASTMONEY_INVENTORY_URL, params=params, timeout=8)
    response.raise_for_status()
    payload = response.json()
    rows = ((payload.get("result") or {}).get("data") or [])
    if not rows:
        return pd.DataFrame(columns=["日期", "库存", "增减"])

    data = pd.DataFrame(rows)
    data = data.rename(
        columns={
            "TRADE_DATE": "日期",
            "ON_WARRANT_NUM": "库存",
            "ADDCHANGE": "增减",
        }
    )
    data = data[["日期", "库存", "增减"]]
    data["日期"] = pd.to_datetime(data["日期"], errors="coerce").dt.date
    data["库存"] = pd.to_numeric(data["库存"], errors="coerce")
    data["增减"] = pd.to_numeric(data["增减"], errors="coerce")
    data = data.dropna(subset=["日期", "库存"]).sort_values("日期").reset_index(drop=True)
    return data


def change_row(data: pd.DataFrame, days: int) -> dict[str, float | None]:
    latest = clean_number(data.iloc[-1].get("库存"))
    if latest is None or len(data) <= days:
        return {"base": None, "change": None, "pct": None}
    base = clean_number(data.iloc[-days - 1].get("库存"))
    if base is None:
        return {"base": None, "change": None, "pct": None}
    change = latest - base
    pct = change / base if base else None
    return {"base": base, "change": change, "pct": pct}


def percentile_rank(series: pd.Series, value: Any) -> float | None:
    number = clean_number(value)
    values = pd.to_numeric(series, errors="coerce").dropna()
    if number is None or len(values) < 5:
        return None
    return clean_number((values <= number).sum() / len(values))


def consecutive_change_days(data: pd.DataFrame) -> int:
    changes = pd.to_numeric(data["增减"], errors="coerce").dropna().tolist()
    if not changes or changes[-1] == 0:
        return 0
    sign = 1 if changes[-1] > 0 else -1
    count = 0
    for value in reversed(changes):
        if value == 0 or (value > 0) != (sign > 0):
            break
        count += 1
    return count * sign


def build_signals(
    changes: dict[int, dict[str, float | None]],
    percentile: float | None,
    streak: int,
) -> list[dict[str, Any]]:
    items = []
    day_change = changes[1]
    if abs(day_change.get("pct") or 0) >= 0.05:
        items.append(
            signal(
                "单日仓单大幅变化",
                "仓单单日变化超过5%，需要结合价格方向观察交割压力或库存去化。",
                level="watch",
                period="day",
                value=ratio_text(day_change.get("pct")),
                threshold="abs >=5%",
            )
        )

    change_20 = changes[20]
    if abs(change_20.get("pct") or 0) >= 0.15:
        direction = "增加" if (change_20.get("change") or 0) > 0 else "减少"
        items.append(
            signal(
                f"近20日仓单明显{direction}",
                f"近20日仓单{direction}超过15%，基本面库存线索需要纳入决策考量。",
                level="watch",
                period="day",
                value=ratio_text(change_20.get("pct")),
                threshold="abs >=15%",
            )
        )

    if percentile is not None and percentile >= 0.85:
        items.append(
            signal(
                "仓单处于高分位",
                "当前仓单处于近期高位，若价格走弱，需要警惕库存压力放大。",
                level="info",
                period="day",
                value=ratio_text(percentile),
                threshold=">=85%",
            )
        )
    elif percentile is not None and percentile <= 0.15:
        items.append(
            signal(
                "仓单处于低分位",
                "当前仓单处于近期低位，若价格走强，库存端可能形成配合线索。",
                level="info",
                period="day",
                value=ratio_text(percentile),
                threshold="<=15%",
            )
        )

    if abs(streak) >= 3:
        direction = "增加" if streak > 0 else "减少"
        items.append(
            signal(
                f"仓单连续{direction}",
                f"仓单已连续{abs(streak)}个交易日{direction}，说明库存变化方向较一致。",
                level="info",
                period="day",
                value=f"{abs(streak)}日",
                threshold=">=3日",
            )
        )
    return items


def unavailable(title: str, note: str) -> dict[str, Any]:
    return module_result(
        "warehouse_receipts",
        title,
        "暂无可用仓单库存数据。",
        priority=10,
        status="unavailable",
        notes=[note],
    )


def signed_number(value: Any) -> str:
    number = clean_number(value, 0)
    if number is None:
        return "-"
    return f"{number:+g}"


def ratio_text(value: Any) -> str:
    number = clean_number(value)
    return "-" if number is None else pct_text(number * 100)


def _signal_priority(item: dict[str, Any]) -> int:
    return {"critical": 80, "watch": 68, "info": 55}.get(item.get("level"), 45)
