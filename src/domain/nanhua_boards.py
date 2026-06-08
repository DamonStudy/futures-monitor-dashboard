"""Map internal contract boards to Nanhua commodity index labels."""

from __future__ import annotations

from typing import Any

# Internal monitor board -> (Nanhua index code, display label)
INTERNAL_BOARD_TO_NANHUA: dict[str, tuple[str | None, str]] = {
    "黑色": ("NHFI", "南华黑色"),
    "有色": ("NHNFI", "南华有色金属"),
    "能化": ("NHECI", "南华能化"),
    "农产品": ("NHAI", "南华农产品"),
    "软商品": ("NHAI", "南华农产品"),
    "贵金属": ("NHPMI", "南华贵金属"),
    "金融": (None, "金融"),
    "航运": (None, "航运"),
}


def resolve_nanhua_board(board: str | None) -> dict[str, Any]:
    internal = board or "未分类"
    code, label = INTERNAL_BOARD_TO_NANHUA.get(internal, (None, internal))
    return {
        "board": internal,
        "nanhua_board": label,
        "nanhua_index_code": code,
        "nanhua_index_id": f"{code}.NH" if code else None,
    }
