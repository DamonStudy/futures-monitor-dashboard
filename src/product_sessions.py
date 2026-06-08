"""Static trading session profiles by product — basic variety metadata."""

from __future__ import annotations

from typing import Any

COMMODITY_DAY = "09:00–10:15、10:30–11:30、13:30–15:00"
FINANCIAL_DAY = "09:30–11:30、13:00–15:00"
NIGHT_21_23 = "21:00–23:00"
NIGHT_21_01 = "21:00–次日01:00"
NIGHT_21_0230 = "21:00–次日02:30"


def _profile(
    *,
    has_night: bool,
    day_session: str,
    night_session: str = "",
) -> dict[str, Any]:
    return {
        "has_night": has_night,
        "night_session": night_session,
        "day_session": day_session,
        "label": "有夜盘" if has_night else "无夜盘",
    }


def _commodity_night(night_session: str = NIGHT_21_23) -> dict[str, Any]:
    return _profile(has_night=True, day_session=COMMODITY_DAY, night_session=night_session)


def _commodity_day_only() -> dict[str, Any]:
    return _profile(has_night=False, day_session=COMMODITY_DAY)


def _financial_day_only() -> dict[str, Any]:
    return _profile(has_night=False, day_session=FINANCIAL_DAY)


# Product code -> session profile. Update when exchanges change trading hours.
# 无夜盘参考：郑商所 AP/CJ/PK/SF/SM/UR 等；大商所 JD/LH；广期所 SI；中金所全品种。
PRODUCT_SESSIONS: dict[str, dict[str, Any]] = {
    # 黑色
    "rb": _commodity_night(),
    "hc": _commodity_night(),
    "i": _commodity_night(),
    "jm": _commodity_night(),
    "j": _commodity_night(),
    "sf": _commodity_day_only(),
    "sm": _commodity_day_only(),
    # 有色
    "cu": _commodity_night(NIGHT_21_01),
    "al": _commodity_night(NIGHT_21_01),
    "zn": _commodity_night(NIGHT_21_01),
    "pb": _commodity_night(NIGHT_21_01),
    "ni": _commodity_night(NIGHT_21_01),
    "sn": _commodity_night(NIGHT_21_01),
    "ao": _commodity_night(NIGHT_21_01),
    "si": _commodity_day_only(),
    # 能化
    "sc": _commodity_night(NIGHT_21_0230),
    "fu": _commodity_night(),
    "lu": _commodity_night(),
    "bu": _commodity_night(),
    "ru": _commodity_night(),
    "nr": _commodity_night(),
    "ta": _commodity_night(),
    "pf": _commodity_night(),
    "px": _commodity_night(),
    "ma": _commodity_night(),
    "eg": _commodity_night(),
    "l": _commodity_night(),
    "pp": _commodity_night(),
    "v": _commodity_night(),
    "eb": _commodity_night(),
    "pg": _commodity_night(),
    "sa": _commodity_night(),
    "fg": _commodity_night(),
    "ur": _commodity_day_only(),
    # 农产品
    "a": _commodity_night(),
    "b": _commodity_night(),
    "m": _commodity_night(),
    "y": _commodity_night(),
    "p": _commodity_night(),
    "rm": _commodity_night(),
    "oi": _commodity_night(),
    "c": _commodity_night(),
    "cs": _commodity_night(),
    "jd": _commodity_day_only(),
    "lh": _commodity_day_only(),
    # 软商品
    "sr": _commodity_night(),
    "cf": _commodity_night(),
    "ap": _commodity_day_only(),
    "cj": _commodity_day_only(),
    "pk": _commodity_day_only(),
    # 贵金属
    "au": _commodity_night(NIGHT_21_0230),
    "ag": _commodity_night(NIGHT_21_0230),
    # 金融
    "if": _financial_day_only(),
    "ih": _financial_day_only(),
    "ic": _financial_day_only(),
    "im": _financial_day_only(),
    "ts": _financial_day_only(),
    "tf": _financial_day_only(),
    "t": _financial_day_only(),
    "tl": _financial_day_only(),
    # 航运
    "ec": _commodity_night(),
}


def get_product_session(product: str | None) -> dict[str, Any] | None:
    if not product:
        return None
    profile = PRODUCT_SESSIONS.get(product.lower())
    if not profile:
        return None
    return {**profile, "source": "catalog"}
