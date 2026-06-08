"""Map CCIDX commodity indices to representative futures constituents."""

from __future__ import annotations

from typing import Any

from ..contracts import BOARDS


def _board_products(*board_names: str) -> list[str]:
    items: list[str] = []
    for board in board_names:
        items.extend(name for name, _ in BOARDS.get(board, []))
    return items


INDEX_CATALOG: dict[str, dict[str, str]] = {
    "100001.CCI": {
        "series_id": "cci",
        "series_name": "中证商品期货指数系列",
        "index_code": "100001",
        "level": "总指数",
    },
    "606001.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606001",
        "level": "总指数",
    },
    "606002.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606002",
        "level": "板块",
    },
    "606003.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606003",
        "level": "子板块",
    },
    "606004.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606004",
        "level": "子板块",
    },
    "606005.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606005",
        "level": "子板块",
    },
    "606006.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606006",
        "level": "子板块",
    },
    "606007.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606007",
        "level": "子板块",
    },
    "606008.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606008",
        "level": "子板块",
    },
    "606009.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606009",
        "level": "板块",
    },
    "606010.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606010",
        "level": "子板块",
    },
    "606011.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606011",
        "level": "子板块",
    },
    "606012.CCI": {
        "series_id": "cfmmc",
        "series_name": "中证监控系列",
        "index_code": "606012",
        "level": "子板块",
    },
    "NHCI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHCI",
        "level": "总指数",
    },
    "NHII.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHII",
        "level": "板块",
    },
    "NHAI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHAI",
        "level": "板块",
    },
    "NHMI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHMI",
        "level": "板块",
    },
    "NHECI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHECI",
        "level": "板块",
    },
    "NHFI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHFI",
        "level": "板块",
    },
    "NHNFI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHNFI",
        "level": "板块",
    },
    "NHPMI.NH": {
        "series_id": "nanhua",
        "series_name": "南华商品指数系列",
        "index_code": "NHPMI",
        "level": "板块",
    },
}


def index_catalog_entry(index_id: str) -> dict[str, str]:
    code = str(index_id or "").replace(".CCI", "")
    return INDEX_CATALOG.get(
        index_id,
        {
            "series_id": "cfmmc",
            "series_name": "中证监控系列",
            "index_code": code or "-",
            "level": "板块",
        },
    )


INDEX_CONSTITUENT_SPECS: dict[str, dict[str, Any]] = {
    "100001.CCI": {
        "scope": "境内商品期货综合指数，覆盖主要商品板块。",
        "boards": ["黑色", "有色", "能化", "农产品", "软商品", "贵金属", "航运"],
    },
    "606001.CCI": {
        "scope": "监控中心口径的中国商品期货综合指数。",
        "boards": ["黑色", "有色", "能化", "农产品", "软商品", "贵金属", "航运"],
    },
    "606002.CCI": {
        "scope": "农产品板块相关期货品种。",
        "boards": ["农产品", "软商品"],
    },
    "606003.CCI": {
        "scope": "谷物类期货品种。",
        "products": ["玉米", "淀粉"],
    },
    "606004.CCI": {
        "scope": "饲料产业链相关期货品种。",
        "products": ["豆粕", "菜粕"],
    },
    "606005.CCI": {
        "scope": "油脂油料产业链相关期货品种。",
        "products": ["豆一", "豆二", "豆粕", "豆油", "棕榈油", "菜粕", "菜油"],
    },
    "606006.CCI": {
        "scope": "粮食类期货品种。",
        "products": ["玉米", "豆一"],
    },
    "606007.CCI": {
        "scope": "油脂类期货品种。",
        "products": ["豆油", "棕榈油", "菜油"],
    },
    "606008.CCI": {
        "scope": "软商品板块相关期货品种。",
        "boards": ["软商品"],
    },
    "606009.CCI": {
        "scope": "工业品板块，覆盖黑色、有色、能化、贵金属等工业相关品种。",
        "boards": ["黑色", "有色", "能化", "贵金属"],
    },
    "606010.CCI": {
        "scope": "能源化工板块相关期货品种。",
        "boards": ["能化"],
    },
    "606011.CCI": {
        "scope": "钢铁产业链相关期货品种。",
        "products": ["螺纹钢", "热卷", "铁矿石", "焦煤", "焦炭"],
    },
    "606012.CCI": {
        "scope": "建材产业链相关期货品种。",
        "products": ["玻璃", "纯碱", "PVC"],
    },
}


def build_constituents(index_id: str) -> dict[str, Any]:
    spec = INDEX_CONSTITUENT_SPECS.get(index_id, {})
    groups: list[dict[str, Any]] = []

    if spec.get("boards"):
        for board in spec["boards"]:
            products = _board_products(board)
            if products:
                groups.append({"board": board, "products": products})

    if spec.get("products"):
        groups = [{"board": spec.get("group_label", "主要成分"), "products": list(spec["products"])}]

    products: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for name in group["products"]:
            if name not in seen:
                seen.add(name)
                products.append(name)

    return {
        "scope": spec.get("scope", "暂无编制口径说明。"),
        "product_count": len(products),
        "groups": groups,
        "products": products,
        "note": "成分为编制方案口径映射，便于理解指数属性；年度调样后请以中证商品指数官网为准。",
    }
