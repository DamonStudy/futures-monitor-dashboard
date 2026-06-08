"""Fetch and summarize broad market data for the dashboard home page."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import pandas as pd

from ..sources.macro.drivers import fetch_macro_drivers
from ..sources.market.nanhua_indices import NANHUA_BOARD_INDICES, NANHUA_INTERPRETATIONS, fetch_nanhua_dataframe
from .index_constituents import index_catalog_entry


PERIODS = {
    "1d": 1,
    "5d": 5,
    "20d": 20,
    "60d": 60,
}

FOREIGN_COMMODITIES = [
    ("OIL", "国际原油", "外盘商品", "新浪外盘"),
    ("CL", "WTI原油", "外盘商品", "新浪外盘"),
    ("GC", "COMEX黄金", "外盘商品", "新浪外盘"),
    ("HG", "COMEX铜", "外盘商品", "新浪外盘"),
]

TUSHARE_INDEX_CODES = [
    ("000300.SH", "沪深300"),
    ("000905.SH", "中证500"),
    ("399006.SZ", "创业板指"),
    ("000852.SH", "中证1000"),
]

AKSHARE_INDEX_FALLBACKS = {
    "000300.SH": "sh000300",
    "000905.SH": "sh000905",
    "399006.SZ": "sz399006",
    "000852.SH": "sh000852",
}


@dataclass
class SeriesSpec:
    id: str
    name: str
    group: str
    source: str
    value_unit: str = "level"
    change_kind: str = "pct"
    interpretation: str = ""


def build_global_overview(contract_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build the broad-market home page payload.

    Every data source is isolated. A failed source is reported in ``errors`` but
    does not prevent the rest of the page from rendering.
    """

    errors: list[dict[str, str]] = []
    nanhua_indices = _guard("nanhua_indices", fetch_nanhua_indices, errors) or []
    drivers: list[dict[str, Any]] = []
    drivers.extend(_guard("macro_drivers", fetch_macro_drivers, errors) or [])
    drivers.extend(_guard("foreign_commodities", fetch_foreign_commodities, errors) or [])
    drivers.extend(_guard("stock_risk", fetch_stock_risk, errors) or [])

    from ..macro import build_macro_context

    macro = _guard("macro_context", lambda: build_macro_context(calendar_days=7), errors) or {}

    lead = _nanhua_lead(nanhua_indices)
    board_indices = [row for row in nanhua_indices if row.get("group") != "总指数"]
    heat_leaders = sorted(
        board_indices,
        key=lambda row: _abs_or_negative(row.get("changes", {}).get("20d")),
        reverse=True,
    )[:4]

    from .board_products import build_board_product_matrix
    from .schema import GLOBAL_SNAPSHOT_SCHEMA_VERSION
    from .skills import run_global_market_skills

    board_product_matrix = (
        build_board_product_matrix(contract_items, nanhua_indices)
        if contract_items
        else {"rows": [], "status": "empty", "preview_limit": 10}
    )
    skill_pack = run_global_market_skills(
        nanhua_indices=nanhua_indices,
        drivers=drivers,
        macro=macro,
        contract_items=contract_items,
        board_product_matrix=board_product_matrix,
    )

    return {
        "ok": bool(nanhua_indices or drivers),
        "mode": "global_market",
        "schema_version": GLOBAL_SNAPSHOT_SCHEMA_VERSION,
        "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lead": lead,
        "nanhua_indices": nanhua_indices,
        "drivers": drivers,
        "macro": macro,
        "narrative": skill_pack.get("narrative") or build_narrative(lead, board_indices, drivers, macro),
        "global_skills": skill_pack.get("skills") or [],
        "board_product_matrix": board_product_matrix,
        "heat_leaders": heat_leaders,
        "errors": errors,
    }


def fetch_nanhua_indices() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ts_code, name, group in NANHUA_BOARD_INDICES:
        df = fetch_nanhua_dataframe(ts_code)
        rows.append(
            series_summary(
                df,
                SeriesSpec(
                    id=ts_code,
                    name=name,
                    group=group,
                    source="TuShare 南华指数",
                    interpretation=NANHUA_INTERPRETATIONS.get(ts_code, "南华板块指数。"),
                ),
            )
        )
    return rows


def _nanhua_lead(nanhua_indices: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in nanhua_indices:
        if row.get("index_code") == "NHCI" or row.get("id") == "NHCI.NH":
            return row
    return nanhua_indices[0] if nanhua_indices else None


def fetch_foreign_commodities() -> list[dict[str, Any]]:
    import akshare as ak

    rows = []
    for code, name, group, source in FOREIGN_COMMODITIES:
        df = ak.futures_foreign_hist(symbol=code)
        rows.append(
            series_summary(
                normalize_series(df, "date", "close"),
                SeriesSpec(
                    id=f"foreign_{code.lower()}",
                    name=name,
                    group=group,
                    source=f"{source} {code}",
                    interpretation=foreign_interpretation(code),
                ),
            )
        )
    return rows


def fetch_stock_risk() -> list[dict[str, Any]]:
    rows = []
    for code, name in TUSHARE_INDEX_CODES:
        rows.append(fetch_stock_index(code, name))
    return rows


def fetch_stock_index(ts_code: str, name: str) -> dict[str, Any]:
    token = os.getenv("TUSHARE_TOKEN")
    if token:
        try:
            import tushare as ts

            pro = ts.pro_api(token)
            df = pro.index_daily(ts_code=ts_code, start_date="20250101")
            if not df.empty:
                return series_summary(
                    normalize_series(df, "trade_date", "close", date_format="%Y%m%d"),
                    SeriesSpec(
                        id=f"stock_{ts_code.lower().replace('.', '_')}",
                        name=name,
                        group="股票风险偏好",
                        source="TuShare",
                        interpretation="A股风险偏好变量，辅助判断商品交易情绪和宏观风险偏好。",
                    ),
                )
        except Exception:
            pass

    import akshare as ak

    fallback = AKSHARE_INDEX_FALLBACKS.get(ts_code)
    if not fallback:
        raise RuntimeError(f"No stock index fallback for {ts_code}")
    df = ak.stock_zh_index_daily(symbol=fallback)
    return series_summary(
        normalize_series(df, "date", "close"),
        SeriesSpec(
            id=f"stock_{ts_code.lower().replace('.', '_')}",
            name=name,
            group="股票风险偏好",
            source="AkShare/新浪",
            interpretation="A股风险偏好变量，TuShare 不可用时使用 AkShare 兜底。",
        ),
    )


def normalize_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    *,
    date_format: str | None = None,
) -> pd.DataFrame:
    data = df[[date_col, value_col]].copy()
    if date_format:
        data["date"] = pd.to_datetime(data[date_col], format=date_format, errors="coerce").dt.date
    else:
        data["date"] = pd.to_datetime(data[date_col], errors="coerce").dt.date
    data["value"] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    if data.empty:
        raise RuntimeError(f"{date_col}/{value_col} has no clean rows")
    return data[["date", "value"]]


def series_summary(df: pd.DataFrame, spec: SeriesSpec) -> dict[str, Any]:
    latest = df.iloc[-1]
    value = float(latest["value"])
    changes = period_changes(df, spec.change_kind)
    ytd = ytd_change(df, spec.change_kind)
    if ytd is not None:
        changes["ytd"] = ytd
    catalog = index_catalog_entry(spec.id)
    return {
        "id": spec.id,
        "name": spec.name,
        "group": spec.group,
        "index_code": catalog.get("index_code"),
        "series_id": catalog.get("series_id"),
        "series_name": catalog.get("series_name"),
        "level": catalog.get("level") or spec.group,
        "source": spec.source,
        "latest_date": latest["date"].isoformat(),
        "latest_value": clean_number(value),
        "value_label": format_value(value, spec.value_unit),
        "change_kind": spec.change_kind,
        "changes": changes,
        "tone": classify_tone(changes.get("20d")),
        "interpretation": spec.interpretation,
        "summary": driver_summary(spec.name, changes, spec.change_kind),
        "chart": chart_rows(df, 180),
        "rows": len(df),
        "constituents": None,
    }


def period_changes(df: pd.DataFrame, kind: str) -> dict[str, float | None]:
    latest = float(df.iloc[-1]["value"])
    changes: dict[str, float | None] = {}
    for key, offset in PERIODS.items():
        if len(df) <= offset:
            changes[key] = None
            continue
        old = float(df.iloc[-1 - offset]["value"])
        changes[key] = change_value(latest, old, kind)
    return changes


def ytd_change(df: pd.DataFrame, kind: str) -> float | None:
    latest = df.iloc[-1]
    previous_year = df[df["date"].map(lambda date: date.year) < latest["date"].year]
    if previous_year.empty:
        return None
    return change_value(float(latest["value"]), float(previous_year.iloc[-1]["value"]), kind)


def change_value(current: float, old: float, kind: str) -> float | None:
    if old == 0 or math.isnan(current) or math.isnan(old):
        return None
    if kind == "diff_bp":
        return clean_number((current - old) * 100)
    return clean_number((current / old - 1) * 100)


def chart_rows(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    rows = df.tail(limit)
    return [{"time": row["date"].isoformat(), "value": clean_number(row["value"])} for _, row in rows.iterrows()]


def build_narrative(
    lead: dict[str, Any] | None,
    board_indices: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
    macro: dict[str, Any] | None = None,
    *,
    board_stats: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build phenomenon → mechanism → verify narrative for cognition training."""
    phenomenon = _narrative_phenomenon(lead, board_indices)
    mechanism = _narrative_mechanism(lead, board_indices, drivers, macro)
    verify = _narrative_verify(lead, board_indices, drivers, macro)

    return {
        "version": 2,
        "sections": [
            {"key": "phenomenon", "title": "现象", "items": phenomenon},
            {"key": "mechanism", "title": "机制", "items": mechanism},
            {"key": "verify", "title": "待验证", "items": verify},
        ],
    }


def _narrative_phenomenon(
    lead: dict[str, Any] | None,
    board_indices: list[dict[str, Any]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    if lead:
        weekly = lead.get("changes", {}).get("5d")
        ytd = lead.get("changes", {}).get("ytd")
        text = f"{lead['name']}周度{format_change(weekly)}，{_weekly_tone_label(weekly)}"
        if ytd is not None and weekly is not None:
            if ytd > 5 and weekly < -0.5:
                text += f"；年内仍{format_change(ytd)}，短线更像获利回吐而非趋势反转"
            elif ytd < 2 and weekly > 0.5:
                text += f"；年内仅{format_change(ytd)}，周度偏强或意味轮动启动"
        items.append(_narrative_line("商品整体", text))

    scored = _weekly_board_scores(board_indices)
    if scored:
        up = sum(1 for _, change in scored if change > 0)
        down = sum(1 for _, change in scored if change < 0)
        if down > up:
            items.append(
                _narrative_line(
                    "板块面",
                    f"周度多数板块回落（{down} 跌 / {up} 涨），整体偏防守，强势更可能是结构性而非全面做多",
                )
            )
        elif up > down:
            items.append(
                _narrative_line(
                    "板块面",
                    f"周度多数板块上涨（{up} 涨 / {down} 跌），多头氛围仍在，但需看能否扩散到总指数",
                )
            )
        else:
            items.append(
                _narrative_line(
                    "板块面",
                    f"周度涨跌互现（{up} 涨 / {down} 跌），板块分化大于方向共识",
                )
            )

        strongest_row, strongest_chg = max(scored, key=lambda pair: pair[1])
        weakest_row, weakest_chg = min(scored, key=lambda pair: pair[1])
        items.append(
            _narrative_line(
                "相对强弱",
                f"{_short_index_name(strongest_row.get('name', ''))}周度{format_change(strongest_chg)}相对最强，"
                f"{_short_index_name(weakest_row.get('name', ''))}({format_change(weakest_chg)})相对最弱",
            )
        )

        ytd_leaders = sorted(
            board_indices,
            key=lambda row: row.get("changes", {}).get("ytd") or -999,
            reverse=True,
        )
        if ytd_leaders:
            ytd_top = ytd_leaders[0]
            ytd_top_weekly = ytd_top.get("changes", {}).get("5d")
            if (ytd_top.get("changes") or {}).get("ytd", 0) > 8 and (ytd_top_weekly or 0) < 0:
                items.append(
                    _narrative_line(
                        "时间错位",
                        f"{_short_index_name(ytd_top.get('name', ''))}年内仍强"
                        f"({format_change(ytd_top.get('changes', {}).get('ytd'))})，"
                        f"但周度{format_change(ytd_top_weekly)}，主线或在休整",
                    )
                )

    return items[:4]


def _narrative_mechanism(
    lead: dict[str, Any] | None,
    board_indices: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
    macro: dict[str, Any] | None,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    driver_map = {row["id"]: row for row in drivers}
    oil = driver_map.get("foreign_oil") or driver_map.get("foreign_cl")
    us10y = driver_map.get("us10y")
    usdcny = driver_map.get("usdcny_fixing")

    pressures = _macro_pressure_phrases(oil, us10y, usdcny)
    if pressures:
        items.append(
            _narrative_line(
                "宏观背景",
                "；".join(pressures) + "，商品定价更易呈现分化而非齐涨齐跌",
            )
        )

    scored = _weekly_board_scores(board_indices)
    if scored:
        strongest_row, _ = max(scored, key=lambda pair: pair[1])
        weakest_row, _ = min(scored, key=lambda pair: pair[1])
        strongest_code = strongest_row.get("index_code") or ""
        weakest_code = weakest_row.get("index_code") or ""

        if strongest_code == "NHFI":
            items.append(
                _narrative_line(
                    "板块映射",
                    "黑色周度偏强，更可能来自国内产业链与政策预期，而非全球宏观全面顺风",
                )
            )
        elif strongest_code == "NHECI":
            oil_chg = (oil.get("changes") or {}).get("20d") if oil else None
            if oil_chg is not None and oil_chg <= -2:
                items.append(
                    _narrative_line(
                        "板块映射",
                        "能化周度相对抗跌，说明部分品种定价已从「跟油价」转向自身供需与利润",
                    )
                )
            else:
                items.append(
                    _narrative_line(
                        "板块映射",
                        "能化周度偏强，与成本端或下游开工改善的预期更相关",
                    )
                )

        rate_chg = (us10y.get("changes") or {}).get("20d") if us10y else None
        if weakest_code == "NHPMI" and rate_chg is not None and rate_chg >= 3:
            items.append(
                _narrative_line(
                    "板块映射",
                    "贵金属周度偏弱，与利率上行压制估值/避险需求的逻辑一致",
                )
            )
        elif weakest_code == "NHAI" and lead and (lead.get("changes") or {}).get("5d", 0) < 0:
            items.append(
                _narrative_line(
                    "板块映射",
                    "农产品周度落后，在整体偏防守环境中缺少独立资金主题时容易被边缘化",
                )
            )

    surprise = _macro_surprise_release(macro)
    if surprise:
        direction = "高于" if surprise.get("beat") == "above" else "低于"
        items.append(
            _narrative_line(
                "数据意外",
                f"{surprise.get('title')}公布{surprise.get('actual')}{surprise.get('unit', '')}，"
                f"{direction}预期，宏观叙事需纳入这一偏差",
            )
        )

    if lead and board_indices and not items:
        items.append(
            _narrative_line(
                "定价逻辑",
                commodity_lead_conclusion(lead.get("changes", {}).get("20d")),
            )
        )

    return items[:5]


def _narrative_verify(
    lead: dict[str, Any] | None,
    board_indices: list[dict[str, Any]],
    drivers: list[dict[str, Any]],
    macro: dict[str, Any] | None,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    driver_map = {row["id"]: row for row in drivers}
    oil = driver_map.get("foreign_oil") or driver_map.get("foreign_cl")
    us10y = driver_map.get("us10y")

    scored = _weekly_board_scores(board_indices)
    if scored and lead:
        strongest_row, strongest_chg = max(scored, key=lambda pair: pair[1])
        weakest_row, weakest_chg = min(scored, key=lambda pair: pair[1])
        lead_weekly = lead.get("changes", {}).get("5d")
        if strongest_chg is not None and (lead_weekly is None or strongest_chg > lead_weekly):
            items.append(
                _narrative_line(
                    "板块延续",
                    f"关注{_short_index_name(strongest_row.get('name', ''))}能否连续两周跑赢南华商品总指数",
                )
            )
        spread = strongest_chg - weakest_chg if strongest_chg is not None and weakest_chg is not None else 0
        if spread >= 2:
            items.append(
                _narrative_line(
                    "分化收敛",
                    f"若最弱链条({_short_index_name(weakest_row.get('name', ''))})止跌"
                    f"或最强板块回撤，说明本轮轮动可能进入尾声",
                )
            )

    if us10y:
        rate_chg = us10y.get("changes", {}).get("20d")
        if rate_chg is not None and rate_chg >= 3:
            items.append(
                _narrative_line(
                    "利率路径",
                    "美债 10Y 若止升或回落，贵金属与工业金属情绪或迎来修复窗口",
                )
            )
        elif rate_chg is not None and rate_chg <= -3:
            items.append(
                _narrative_line(
                    "利率路径",
                    "美债 10Y 若重新上行，需警惕风险偏好回落对商品的再压制",
                )
            )

    if oil:
        oil_chg = oil.get("changes", {}).get("20d")
        if oil_chg is not None and oil_chg <= -2:
            items.append(
                _narrative_line(
                    "成本锚",
                    "原油能否在当前水平企稳，决定能化是跟涨、分化还是继续受成本拖累",
                )
            )

    calendar = (macro or {}).get("calendar") or {}
    next_event = calendar.get("next_event")
    if calendar.get("risk_window_48h") and next_event:
        items.append(
            _narrative_line(
                "事件风险",
                f"未来 48h 关注{next_event.get('region')} · {next_event.get('title')}，"
                f"数据落地前后宜控制杠杆与隔夜敞口",
            )
        )
    elif next_event:
        items.append(
            _narrative_line(
                "事件日历",
                f"下一关注 {next_event.get('date')} {next_event.get('region')} · {next_event.get('title')}",
            )
        )

    if not items and lead:
        items.append(
            _narrative_line(
                "方向确认",
                "观察南华商品总指数周度能否延续当前方向，并同步核对核心变量是否同向",
            )
        )

    return items[:4]


def _weekly_board_scores(board_indices: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    scored: list[tuple[dict[str, Any], float]] = []
    for row in board_indices:
        change = row.get("changes", {}).get("5d")
        if change is None:
            continue
        scored.append((row, float(change)))
    return scored


def _weekly_tone_label(change: float | None) -> str:
    if change is None:
        return "方向待确认"
    if change <= -1.5:
        return "整体明显偏弱"
    if change < -0.3:
        return "整体小幅走弱"
    if change >= 1.5:
        return "整体明显偏强"
    if change > 0.3:
        return "整体小幅走强"
    return "整体大致持平"


def _macro_pressure_phrases(
    oil: dict[str, Any] | None,
    us10y: dict[str, Any] | None,
    usdcny: dict[str, Any] | None,
) -> list[str]:
    phrases: list[str] = []
    if us10y:
        rate_chg = us10y.get("changes", {}).get("20d")
        if rate_chg is not None and rate_chg >= 3:
            phrases.append("海外利率上行、金融条件偏紧")
        elif rate_chg is not None and rate_chg <= -3:
            phrases.append("海外利率回落、金融条件趋松")
    if oil:
        oil_chg = oil.get("changes", {}).get("20d")
        if oil_chg is not None and oil_chg <= -2:
            phrases.append("原油走弱、成本锚下移")
        elif oil_chg is not None and oil_chg >= 2:
            phrases.append("原油走强、成本端有支撑")
    if usdcny:
        fx_chg = usdcny.get("changes", {}).get("20d")
        if fx_chg is not None and fx_chg <= -0.3:
            phrases.append("人民币偏强、进口成本下降")
        elif fx_chg is not None and fx_chg >= 0.3:
            phrases.append("人民币偏弱、进口成本抬升")
    return phrases


def _macro_surprise_release(macro: dict[str, Any] | None) -> dict[str, Any] | None:
    if not macro or macro.get("status") == "unavailable":
        return None
    releases = (macro.get("snapshot") or {}).get("releases") or []
    for row in releases:
        if row.get("beat") in {"above", "below"} and not row.get("pending"):
            return row
    return None


def _short_index_name(name: str) -> str:
    text = str(name or "").strip()
    for token in ("南华", "指数"):
        text = text.replace(token, "")
    return text or name


def _narrative_line(label: str, text: str) -> dict[str, str]:
    return {"label": label, "text": text}


def commodity_lead_conclusion(change_20d: float | None) -> str:
    if change_20d is None:
        return "整体方向待确认，暂以结构性机会为主。"
    if change_20d <= -3:
        return "商品整体偏弱，盘面偏防守，强势品种更可能是结构性行情而非全面做多环境。"
    if change_20d < -1:
        return "商品整体偏弱，优先盯抗跌板块，不宜按全面牛市思路配置。"
    if change_20d >= 3:
        return "商品整体偏强，多头氛围占优，重点看强势板块能否形成共振扩散。"
    if change_20d > 1:
        return "商品整体偏强，可逐步提高对趋势延续的权重。"
    return "商品整体中性震荡，方向确认前以板块分化交易为主。"


def board_rotation_conclusion(strongest: dict[str, Any], weakest: dict[str, Any]) -> str:
    s_chg = strongest.get("changes", {}).get("20d") or 0
    w_chg = weakest.get("changes", {}).get("20d") or 0
    spread = s_chg - w_chg
    if spread >= 3:
        return "板块分化明显，决策上应优先强势板块、回避最弱链条。"
    if s_chg < 0 and w_chg < 0:
        return "多数板块同步走弱，更像系统性调整，强势板块仅具相对意义。"
    return "强弱分化仍在，可按板块优先级分配关注度。"


def oil_conclusion(change_20d: float | None) -> str:
    if change_20d is None:
        return "原油方向不明，能化板块暂缺清晰成本锚。"
    if change_20d <= -5:
        return "成本端大幅下移，化工品定价更看自身供需，不宜单纯按成本上涨逻辑做多能化。"
    if change_20d <= -2:
        return "成本端压力减轻，若需求端无恶化，下游利润修复预期偏强。"
    if change_20d >= 5:
        return "成本端显著抬升，关注化工品跟涨与利润再分配，能化多头需有成本支撑逻辑。"
    if change_20d >= 2:
        return "成本端有支撑，能化板块可偏多看待跟涨品种。"
    return "原油波动有限，能化板块仍以品种自身逻辑为主。"


def us10y_conclusion(change_20d_bp: float | None) -> str:
    if change_20d_bp is None:
        return "利率方向待观察，宏观定价暂非主导。"
    if change_20d_bp >= 8:
        return "金融条件收紧，对商品估值和贵金属通常偏压制，多头需降低久期与杠杆预期。"
    if change_20d_bp >= 3:
        return "利率温和上行，外部流动性预期偏紧，商品全面做多的宏观背景不足。"
    if change_20d_bp <= -8:
        return "金融条件趋松，有利于风险偏好修复，贵金属和工业商品情绪偏友好。"
    if change_20d_bp <= -3:
        return "利率回落，外部流动性预期改善，对商品多头是边际利好。"
    return "利率变化不大，宏观并非当前商品定价主驱动。"


def usdcny_conclusion(change_20d_pct: float | None) -> str:
    """Interpret change in USD/CNY fixing: positive = USD stronger."""
    if change_20d_pct is None:
        return "汇率影响有限，内外盘价差暂非核心矛盾。"
    if change_20d_pct >= 0.8:
        return "人民币偏弱，进口成本抬升，内盘相对外盘锚定品种或偏强，但压制进口利润。"
    if change_20d_pct >= 0.3:
        return "人民币温和贬值，进口成本略升，关注内外盘正基差品种的进口窗口变化。"
    if change_20d_pct <= -0.8:
        return "人民币偏强，进口成本回落，内盘相对外盘计价品种承压，但有利于降低输入型通胀。"
    if change_20d_pct <= -0.3:
        return "人民币温和升值，进口原料成本下降，出口竞争型品种需关注估值压力。"
    return "汇率波动不大，内外盘价差驱动有限。"


def driver_summary(name: str, changes: dict[str, float | None], kind: str) -> str:
    return f"近20日{format_change(changes.get('20d'), kind)}，近60日{format_change(changes.get('60d'), kind)}。"


def classify_tone(change: float | None) -> str:
    if change is None:
        return "neutral"
    if change >= 2:
        return "up"
    if change <= -2:
        return "down"
    return "neutral"


def format_value(value: float, unit: str) -> str:
    if unit == "percent":
        return f"{value:.2f}%"
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.4f}"


def format_change(value: float | None, kind: str = "pct") -> str:
    if value is None:
        return "暂无数据"
    if kind == "diff_bp":
        return f"{value:+.1f}bp"
    return f"{value:+.2f}%"


def clean_number(value: Any, digits: int = 4) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def foreign_interpretation(code: str) -> str:
    if code in {"OIL", "CL"}:
        return "原油是能化成本中枢，也影响全球通胀和风险偏好。"
    if code == "GC":
        return "黄金反映实际利率、避险需求和美元金融条件。"
    if code == "HG":
        return "铜常被用作全球工业需求和制造业景气的观察变量。"
    return "外盘商品变量，用于观察海外定价和内外盘联动。"


def _guard(name: str, fn: Callable[[], Any], errors: list[dict[str, str]]) -> Any:
    try:
        return fn()
    except Exception as exc:
        errors.append({"source": name, "message": str(exc)})
        return None


def _abs_or_negative(value: float | None) -> float:
    return abs(value) if value is not None else -1
