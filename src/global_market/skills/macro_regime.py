"""Global macro regime skill — interprets cross-asset drivers for commodity backdrop."""

from __future__ import annotations

from typing import Any

from ...schemas.output import signal, skill_result
from ..overview import us10y_conclusion, usdcny_conclusion, oil_conclusion

SKILL_ID = "macro_regime"
TITLE = "宏观环境"
PRIORITY = 60


def analyze(ctx: dict[str, Any]) -> dict[str, Any]:
    driver_map = ctx.get("driver_map") or {}
    macro = ctx.get("macro") or {}
    oil = driver_map.get("foreign_oil") or driver_map.get("foreign_cl")
    us10y = driver_map.get("us10y")
    usdcny = driver_map.get("usdcny_fixing")

    if not oil and not us10y and not usdcny and macro.get("status") == "unavailable":
        return skill_result(
            SKILL_ID,
            TITLE,
            "核心变量暂不可用，宏观背景无法判断。",
            status="unavailable",
            priority=20,
        )

    signals: list[dict[str, Any]] = []
    pressures: list[str] = []

    if us10y:
        rate_chg = (us10y.get("changes") or {}).get("20d")
        signals.append(
            signal(
                "海外利率",
                us10y_conclusion(rate_chg),
                level=_level_from_bp(rate_chg),
                period="20d",
                value=rate_chg,
            )
        )
        if rate_chg is not None and rate_chg >= 3:
            pressures.append("金融条件偏紧")
        elif rate_chg is not None and rate_chg <= -3:
            pressures.append("金融条件趋松")

    if oil:
        oil_chg = (oil.get("changes") or {}).get("20d")
        signals.append(
            signal(
                "原油成本锚",
                oil_conclusion(oil_chg),
                level=_level_from_pct(oil_chg),
                period="20d",
                value=oil_chg,
            )
        )
        if oil_chg is not None and oil_chg <= -2:
            pressures.append("成本端下移")
        elif oil_chg is not None and oil_chg >= 2:
            pressures.append("成本端抬升")

    if usdcny:
        fx_chg = (usdcny.get("changes") or {}).get("20d")
        signals.append(
            signal(
                "人民币汇率",
                usdcny_conclusion(fx_chg),
                level="info",
                period="20d",
                value=fx_chg,
            )
        )

    surprise = _macro_surprise(macro)
    if surprise:
        direction = "高于" if surprise.get("beat") == "above" else "低于"
        signals.append(
            signal(
                "数据意外",
                f"{surprise.get('title')}公布{surprise.get('actual')}{surprise.get('unit', '')}，"
                f"{direction}预期，需修正宏观叙事",
                level="watch",
            )
        )

    if pressures:
        summary = f"当前组合：{'、'.join(pressures)}，商品更易分化定价"
    elif signals:
        summary = "宏观变量波动有限，商品更多受板块自身逻辑驱动"
    else:
        summary = "宏观背景中性"

    return skill_result(
        SKILL_ID,
        TITLE,
        summary,
        priority=PRIORITY,
        signals=signals,
        notes=["大盘宏观 skill：只读核心变量与宏观发布，不调用品种 Playbook。"],
    )


def _macro_surprise(macro: dict[str, Any]) -> dict[str, Any] | None:
    releases = (macro.get("snapshot") or {}).get("releases") or []
    for row in releases:
        if row.get("beat") in {"above", "below"} and not row.get("pending"):
            return row
    return None


def _level_from_bp(value: float | None) -> str:
    if value is None:
        return "info"
    if abs(value) >= 8:
        return "critical"
    if abs(value) >= 3:
        return "watch"
    return "info"


def _level_from_pct(value: float | None) -> str:
    if value is None:
        return "info"
    if abs(value) >= 5:
        return "critical"
    if abs(value) >= 2:
        return "watch"
    return "info"
