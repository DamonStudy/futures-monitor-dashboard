"""Fetch Nanhua commodity board indices via TuShare."""

from __future__ import annotations

import os

import pandas as pd

NANHUA_BOARD_INDICES = [
    ("NHCI.NH", "南华商品指数", "总指数"),
    ("NHII.NH", "南华工业品指数", "板块"),
    ("NHAI.NH", "南华农产品指数", "板块"),
    ("NHMI.NH", "南华金属指数", "板块"),
    ("NHECI.NH", "南华能化指数", "板块"),
    ("NHFI.NH", "南华黑色指数", "板块"),
    ("NHNFI.NH", "南华有色金属指数", "板块"),
    ("NHPMI.NH", "南华贵金属指数", "板块"),
]

NANHUA_INTERPRETATIONS = {
    "NHCI.NH": "南华全商品标尺，适合判断商品整体冷热与板块轮动背景。",
    "NHII.NH": "工业相关商品板块，覆盖黑色、有色、能化、贵金属等。",
    "NHAI.NH": "农产品板块强弱，便于和工业品指数对比。",
    "NHMI.NH": "金属板块（含有色与贵金属权重），观察工业金属整体。",
    "NHECI.NH": "能源化工链条，与原油及化工品情绪高度相关。",
    "NHFI.NH": "黑色产业链，螺纹、铁矿、双焦等方向的代表。",
    "NHNFI.NH": "有色金属板块，全球制造业与宏观风险偏好参照。",
    "NHPMI.NH": "贵金属板块，利率、美元与避险需求的重要窗口。",
}


def fetch_nanhua_dataframe(ts_code: str, *, start_date: str = "20240101") -> pd.DataFrame:
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("未配置 TUSHARE_TOKEN，无法拉取南华指数。")

    import tushare as ts

    pro = ts.pro_api(token)
    df = pro.fut_index_daily(ts_code=ts_code, start_date=start_date)
    if df is None or df.empty:
        raise RuntimeError(f"{ts_code} returned no rows from fut_index_daily")

    data = df[["trade_date", "close"]].copy()
    data["date"] = pd.to_datetime(data["trade_date"], format="%Y%m%d", errors="coerce").dt.date
    data["value"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    if data.empty:
        raise RuntimeError(f"{ts_code} has no clean rows")
    return data[["date", "value"]]
