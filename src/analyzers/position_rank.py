"""Seat-level futures position ranking diagnostics from Sina."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import akshare as ak
import pandas as pd

from .basis import position_query_dates, resolve_dominant_contract
from .schema import signal, module_result, table
from .utils import clean_number


RANK_TYPES = ("成交量", "多单持仓", "空单持仓")


def analyze(meta: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    contract = resolve_contract(meta, quote)
    if not contract:
        return unavailable("无法识别实际主力合约。")

    rankings: dict[str, pd.DataFrame] = {}
    used_date: str | None = None
    last_error: Exception | None = None
    for date in position_query_dates(meta, quote):
        try:
            candidate = {rank_type: fetch_rank(rank_type, contract, date) for rank_type in RANK_TYPES}
        except Exception as exc:
            last_error = exc
            continue
        if any(len(df) > 0 for df in candidate.values()):
            rankings = candidate
            used_date = date
            break

    if not rankings:
        if last_error:
            return unavailable(f"席位持仓请求失败：{last_error}")
        return unavailable("该合约当前日期暂无席位持仓数据。")

    long_df = rankings["多单持仓"]
    short_df = rankings["空单持仓"]
    volume_df = rankings["成交量"]
    stats = summarize(long_df, short_df, volume_df)
    signals = build_signals(stats)
    priority = max([45] + [_signal_priority(item) for item in signals])

    summary = (
        f"{contract}席位榜：Top20多单{int_text(stats['long_total'])}，"
        f"空单{int_text(stats['short_total'])}，"
        f"净持仓{signed_number(stats['net_position'])}；"
        f"多单较上日{signed_number(stats['long_change'])}，空单{signed_number(stats['short_change'])}。"
    )

    return module_result(
        "position_rank",
        "席位持仓",
        summary,
        priority=priority,
        signals=signals,
        tables=[
            table(
                "席位汇总",
                ["指标", "数值"],
                [
                    {"指标": "合约", "数值": contract},
                    {"指标": "日期", "数值": used_date or "-"},
                    {"指标": "Top20多单", "数值": int_text(stats["long_total"])},
                    {"指标": "Top20空单", "数值": int_text(stats["short_total"])},
                    {"指标": "Top20净持仓", "数值": signed_number(stats["net_position"])},
                    {"指标": "多单增减", "数值": signed_number(stats["long_change"])},
                    {"指标": "空单增减", "数值": signed_number(stats["short_change"])},
                    {"指标": "净持仓增减", "数值": signed_number(stats["net_change"])},
                    {"指标": "多头Top5集中度", "数值": ratio_text(stats["long_top5_ratio"])},
                    {"指标": "空头Top5集中度", "数值": ratio_text(stats["short_top5_ratio"])},
                    {"指标": "成交Top5集中度", "数值": ratio_text(stats["volume_top5_ratio"])},
                ],
            ),
            table(
                "前五席位",
                ["类型", "名次", "会员简称", "数值", "比上交易增减"],
                top_rows(rankings),
            ),
        ],
        notes=["该口径来自新浪期货成交持仓榜，按具体合约和日期查询，适合观察席位结构变化。"],
    )


def resolve_contract(meta: dict[str, Any], quote: dict[str, Any]) -> str | None:
    contract = sina_contract(quote.get("underlying_symbol") or quote.get("symbol") or meta.get("symbol"))
    if contract:
        return contract
    return resolve_dominant_contract(meta, quote)


def sina_contract(symbol: Any) -> str | None:
    if not symbol:
        return None
    tail = str(symbol).split("@")[-1].split(".")[-1]
    match = re.fullmatch(r"([A-Za-z]+)([0-9]{3,4})", tail)
    if not match:
        return None
    return f"{match.group(1).upper()}{match.group(2)}"


@lru_cache(maxsize=512)
def fetch_rank(rank_type: str, contract: str, date: str) -> pd.DataFrame:
    data = ak.futures_hold_pos_sina(symbol=rank_type, contract=contract, date=date)
    data = data.copy()
    for column in data.columns:
        if column not in ("会员简称",):
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def summarize(
    long_df: pd.DataFrame,
    short_df: pd.DataFrame,
    volume_df: pd.DataFrame,
) -> dict[str, float | None]:
    long_total = column_sum(long_df, "多单持仓")
    short_total = column_sum(short_df, "空单持仓")
    long_change = column_sum(long_df, "比上交易增减")
    short_change = column_sum(short_df, "比上交易增减")
    return {
        "long_total": long_total,
        "short_total": short_total,
        "net_position": safe_subtract(long_total, short_total),
        "long_change": long_change,
        "short_change": short_change,
        "net_change": safe_subtract(long_change, short_change),
        "long_top5_ratio": top_ratio(long_df, "多单持仓", 5),
        "short_top5_ratio": top_ratio(short_df, "空单持仓", 5),
        "volume_top5_ratio": top_ratio(volume_df, "成交量", 5),
    }


def column_sum(data: pd.DataFrame, column: str) -> float | None:
    if column not in data:
        return None
    value = pd.to_numeric(data[column], errors="coerce").sum()
    return clean_number(value, 0)


def safe_subtract(left: Any, right: Any) -> float | None:
    left_num = clean_number(left)
    right_num = clean_number(right)
    if left_num is None or right_num is None:
        return None
    return left_num - right_num


def top_ratio(data: pd.DataFrame, column: str, limit: int) -> float | None:
    if column not in data or len(data) == 0:
        return None
    values = pd.to_numeric(data[column], errors="coerce").dropna()
    total = values.sum()
    if total == 0:
        return None
    return clean_number(values.head(limit).sum() / total)


def top_rows(rankings: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    rows = []
    value_column = {"成交量": "成交量", "多单持仓": "多单持仓", "空单持仓": "空单持仓"}
    for rank_type, data in rankings.items():
        column = value_column[rank_type]
        for _, row in data.head(5).iterrows():
            rows.append(
                {
                    "类型": rank_type,
                    "名次": int_text(row.get("名次")),
                    "会员简称": row.get("会员简称"),
                    "数值": int_text(row.get(column)),
                    "比上交易增减": signed_number(row.get("比上交易增减")),
                }
            )
    return rows


def build_signals(stats: dict[str, float | None]) -> list[dict[str, Any]]:
    items = []
    long_total = clean_number(stats.get("long_total"))
    short_total = clean_number(stats.get("short_total"))
    net_position = clean_number(stats.get("net_position"))
    net_change = clean_number(stats.get("net_change"))
    total_position = (long_total or 0) + (short_total or 0)

    if net_position is not None and total_position:
        net_ratio = net_position / total_position
        if abs(net_ratio) >= 0.08:
            side = "净多" if net_ratio > 0 else "净空"
            items.append(
                signal(
                    f"Top20席位{side}",
                    f"Top20多空持仓差占多空合计约{ratio_text(abs(net_ratio))}，席位结构存在方向倾斜。",
                    level="watch",
                    period="day",
                    value=ratio_text(net_ratio),
                    threshold="abs >=8%",
                )
            )

    if net_change is not None and total_position:
        change_ratio = net_change / total_position
        if abs(change_ratio) >= 0.03:
            side = "净多增加" if change_ratio > 0 else "净空增加"
            items.append(
                signal(
                    f"Top20席位{side}",
                    "多空持仓增减变化较明显，需要结合价格方向判断主动增仓还是对冲换手。",
                    level="info",
                    period="day",
                    value=ratio_text(change_ratio),
                    threshold="abs >=3%",
                )
            )

    for key, name in (
        ("long_top5_ratio", "多头Top5集中度较高"),
        ("short_top5_ratio", "空头Top5集中度较高"),
    ):
        ratio = stats.get(key)
        if ratio is not None and ratio >= 0.45:
            items.append(
                signal(
                    name,
                    "前五席位占比较高，后续需要关注头部席位是否继续同向变化。",
                    level="info",
                    period="day",
                    value=ratio_text(ratio),
                    threshold=">=45%",
                )
            )
    return items


def unavailable(note: str) -> dict[str, Any]:
    return module_result(
        "position_rank",
        "席位持仓",
        "暂无可用席位持仓数据。",
        priority=10,
        status="unavailable",
        notes=[note],
    )


def signed_number(value: Any) -> str:
    number = clean_number(value, 0)
    if number is None:
        return "-"
    return f"{number:+,.0f}"


def int_text(value: Any) -> str:
    number = clean_number(value, 0)
    if number is None:
        return "-"
    return f"{number:,.0f}"


def ratio_text(value: Any) -> str:
    number = clean_number(value)
    return "-" if number is None else f"{number * 100:.2f}%"


def _signal_priority(item: dict[str, Any]) -> int:
    return {"critical": 80, "watch": 68, "info": 55}.get(item.get("level"), 45)
