"""Macro market drivers — rates, FX, commodity price index."""

from __future__ import annotations

from typing import Any

import pandas as pd


def fetch_macro_drivers() -> list[dict[str, Any]]:
    import akshare as ak

    from ...global_market.overview import SeriesSpec, normalize_series, series_summary

    rows: list[dict[str, Any]] = []

    commodity = ak.macro_china_commodity_price_index()
    rows.append(
        series_summary(
            normalize_series(commodity, "日期", "最新值"),
            SeriesSpec(
                id="macro_commodity_price",
                name="国内大宗商品价格指数",
                group="国内商品",
                source="东方财富",
                interpretation="国内现货和商品价格氛围，和期货指数互相印证。",
            ),
        )
    )

    rates = ak.bond_zh_us_rate(start_date="20250101")
    rate_specs = [
        ("us10y", "美国10年期国债收益率", "海外利率", "美国国债收益率10年", "利率上行通常压制商品估值和贵金属。"),
        ("cn10y", "中国10年期国债收益率", "国内利率", "中国国债收益率10年", "国内利率变化反映增长和流动性环境。"),
        ("us_curve", "美国10Y-2Y利差", "海外利率", "美国国债收益率10年-2年", "利差走阔偏增长预期，收窄偏紧缩或衰退担忧。"),
    ]
    for item_id, name, group, column, interpretation in rate_specs:
        clean = rates.dropna(subset=[column])
        rows.append(
            series_summary(
                normalize_series(clean, "日期", column),
                SeriesSpec(
                    id=item_id,
                    name=name,
                    group=group,
                    source="东方财富",
                    value_unit="percent",
                    change_kind="diff_bp",
                    interpretation=interpretation,
                ),
            )
        )

    fx = ak.currency_boc_safe()
    fx_data = fx[["日期", "美元"]].copy()
    fx_data["美元兑人民币中间价"] = pd.to_numeric(fx_data["美元"], errors="coerce") / 100
    rows.append(
        series_summary(
            normalize_series(fx_data, "日期", "美元兑人民币中间价"),
            SeriesSpec(
                id="usdcny_fixing",
                name="美元兑人民币中间价",
                group="汇率",
                source="外汇管理局",
                interpretation="人民币走弱通常抬升进口成本和内盘商品计价。",
            ),
        )
    )
    return rows
