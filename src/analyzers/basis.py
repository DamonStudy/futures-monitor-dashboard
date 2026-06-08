"""Spot-futures basis diagnostics from AkShare daily spot price tables."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

import akshare as ak
import pandas as pd

from .schema import module_result, signal, table
from .utils import clean_number, fmt_number, parse_product_symbol, pct_text


# AkShare `dom_basis` = 期货价 - 现货价；负值表示现货相对期货升水。
LOWERCASE_CODES = {"bc", "lc", "lu", "nr", "pd", "ps", "pt", "sc", "si"}
STRONG_BASIS_RATE = 0.02
NEAR_DOM_SPREAD_RATE = 0.01


def analyze(meta: dict[str, Any], quote: dict[str, Any] | None = None) -> dict[str, Any]:
    code = product_code(meta)
    if not code:
        return unavailable("无法识别品种代码。")

    anchor = quote_datetime(quote)
    row, used_date = latest_product_row(code, anchor)
    if row is None:
        return unavailable("该品种暂无公开期现基差数据。")

    spot = clean_number(row.get("spot_price"))
    dom_price = clean_number(row.get("dominant_contract_price"))
    near_price = clean_number(row.get("near_contract_price"))
    dom_basis = clean_number(row.get("dom_basis"))
    near_basis = clean_number(row.get("near_basis"))
    dom_rate = clean_number(row.get("dom_basis_rate"))
    near_rate = clean_number(row.get("near_basis_rate"))
    dominant = str(row.get("dominant_contract") or "").upper()
    near = str(row.get("near_contract") or "").upper()

    structure = basis_structure(dom_basis, dom_rate)
    signals = build_signals(dom_basis, dom_rate, near_basis, near_rate, dominant, near)
    priority = max([45] + [_signal_priority(item) for item in signals])

    summary = (
        f"{used_date} {code} 现货{fmt_number(spot, 2)}，"
        f"主力{dominant or '-'} {fmt_number(dom_price, 2)}，"
        f"基差{signed_number(dom_basis)}（{ratio_text(dom_rate)}），"
        f"{structure}。"
    )

    notes = [
        "口径来自 AkShare 期现价格表：基差=期货-现货，负值表示现货升水。",
        "适合观察期现收敛与现货强弱，不等同于跨期期限结构。",
    ]

    return module_result(
        "basis",
        "期现基差",
        summary,
        priority=priority,
        signals=signals,
        tables=[
            table(
                "基差概览",
                ["项目", "数值"],
                [
                    {"项目": "数据日期", "数值": used_date},
                    {"项目": "现货价", "数值": fmt_number(spot, 2)},
                    {"项目": "近月合约", "数值": near or "-"},
                    {"项目": "近月价", "数值": fmt_number(near_price, 2)},
                    {"项目": "近月基差", "数值": signed_number(near_basis)},
                    {"项目": "近月基差率", "数值": ratio_text(near_rate)},
                    {"项目": "主力合约", "数值": dominant or "-"},
                    {"项目": "主力价", "数值": fmt_number(dom_price, 2)},
                    {"项目": "主力基差", "数值": signed_number(dom_basis)},
                    {"项目": "主力基差率", "数值": ratio_text(dom_rate)},
                    {"项目": "结构判断", "数值": structure},
                ],
            )
        ],
        notes=notes,
    )


def resolve_dominant_contract(meta: dict[str, Any], quote: dict[str, Any] | None = None) -> str | None:
    """Return uppercase dominant contract from basis table, for seat-rank lookups."""
    code = product_code(meta)
    if not code:
        return None
    row, _ = latest_product_row(code, quote_datetime(quote))
    if not row:
        return None
    contract = str(row.get("dominant_contract") or "").strip()
    return contract.upper() if contract else None


def position_query_dates(meta: dict[str, Any], quote: dict[str, Any] | None = None) -> list[str]:
    """Candidate trade dates for seat rankings; DCE often lags one session on Sina."""
    primary = quote_datetime(quote).strftime("%Y%m%d")
    dates = [primary]
    if exchange_id(meta, quote) == "DCE":
        previous = previous_weekday(quote_datetime(quote)).strftime("%Y%m%d")
        if previous not in dates:
            dates.append(previous)
    return dates


def product_code(meta: dict[str, Any]) -> str | None:
    _, product = parse_product_symbol(meta.get("symbol"))
    if not product:
        return None
    product = product.strip()
    return product if product in LOWERCASE_CODES else product.upper()


def exchange_id(meta: dict[str, Any], quote: dict[str, Any] | None = None) -> str | None:
    for symbol in (
        (quote or {}).get("underlying_symbol"),
        (quote or {}).get("symbol"),
        meta.get("symbol"),
    ):
        exchange, _ = parse_product_symbol(symbol)
        if exchange:
            return exchange.upper()
    return None


def latest_product_row(product_code: str, anchor: datetime) -> tuple[dict[str, Any] | None, str | None]:
    for day in candidate_dates(anchor, limit=6):
        date_str = day.strftime("%Y%m%d")
        table_df = fetch_spot_table(date_str)
        row = row_for_product(table_df, product_code)
        if row is not None:
            return row, date_str
    return None, None


def candidate_dates(anchor: datetime, *, limit: int) -> list[date]:
    day = anchor.date()
    dates: list[date] = []
    while len(dates) < limit:
        if day.weekday() < 5:
            dates.append(day)
        day -= timedelta(days=1)
    return dates


def previous_weekday(anchor: datetime) -> datetime:
    day = anchor.date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return datetime.combine(day, anchor.time())


@lru_cache(maxsize=16)
def fetch_spot_table(date_yyyymmdd: str) -> pd.DataFrame:
    df = ak.futures_spot_price(date_yyyymmdd)
    if df is None or df.empty:
        return pd.DataFrame()
    normalized = df.copy()
    if "symbol" in normalized.columns:
        normalized["symbol"] = normalized["symbol"].astype(str).str.upper()
    return normalized


def row_for_product(table_df: pd.DataFrame, product_code: str) -> dict[str, Any] | None:
    if table_df.empty or "symbol" not in table_df.columns:
        return None
    matched = table_df[table_df["symbol"].astype(str).str.upper() == product_code.upper()]
    if matched.empty:
        return None
    return matched.iloc[-1].to_dict()


def quote_datetime(quote: dict[str, Any] | None) -> datetime:
    if quote and quote.get("datetime"):
        parsed = pd.to_datetime(quote["datetime"], errors="coerce")
        if not pd.isna(parsed):
            return parsed.to_pydatetime()
    return datetime.now()


def basis_structure(dom_basis: float | None, dom_rate: float | None) -> str:
    rate = abs(dom_rate or 0)
    if dom_basis is None or dom_rate is None:
        return "基差数据不完整"
    if dom_basis < 0:
        return "现货升水" if rate >= STRONG_BASIS_RATE else "现货小幅升水"
    if dom_basis > 0:
        return "现货贴水" if rate >= STRONG_BASIS_RATE else "现货小幅贴水"
    return "期现平水"


def build_signals(
    dom_basis: float | None,
    dom_rate: float | None,
    near_basis: float | None,
    near_rate: float | None,
    dominant: str,
    near: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    rate = clean_number(dom_rate)
    if rate is not None and abs(rate) >= STRONG_BASIS_RATE:
        side = "现货升水" if (dom_basis or 0) < 0 else "现货贴水"
        items.append(
            signal(
                f"主力基差{side}偏大",
                "期现价差超过2%，现货端相对期货偏强或偏弱，需结合库存与交割逻辑核对。",
                level="watch",
                period="day",
                value=ratio_text(rate),
                threshold="abs >=2%",
            )
        )

    if (
        dom_basis is not None
        and near_basis is not None
        and dominant
        and near
        and dominant != near
    ):
        spread = clean_number(near_basis - dom_basis)
        spot_ref = abs(clean_number(dom_basis) or 1)
        if spread is not None and abs(spread / spot_ref) >= NEAR_DOM_SPREAD_RATE:
            direction = "近月更高" if spread > 0 else "主力更高"
            items.append(
                signal(
                    "近月与主力基差分化",
                    f"近月相对主力基差出现分化（{direction}），可对照跨期结构一起验证。",
                    level="info",
                    period="day",
                    value=signed_number(spread),
                    threshold="spread >=1%",
                )
            )
    return items


def unavailable(note: str) -> dict[str, Any]:
    return module_result(
        "basis",
        "期现基差",
        "暂无可用期现基差数据。",
        priority=10,
        status="unavailable",
        notes=[note],
    )


def signed_number(value: Any) -> str:
    number = clean_number(value, 2)
    if number is None:
        return "-"
    return f"{number:+g}"


def ratio_text(value: Any) -> str:
    number = clean_number(value)
    return "-" if number is None else pct_text(number * 100)


def _signal_priority(item: dict[str, Any]) -> int:
    return {"critical": 80, "watch": 68, "info": 55}.get(item.get("level"), 45)
