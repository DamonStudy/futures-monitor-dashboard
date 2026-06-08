"""Backward-compatible re-exports — prefer `src.domain.index_constituents`."""

from ..domain.index_constituents import (
    INDEX_CATALOG,
    INDEX_CONSTITUENT_SPECS,
    build_constituents,
    index_catalog_entry,
)

__all__ = [
    "INDEX_CATALOG",
    "INDEX_CONSTITUENT_SPECS",
    "build_constituents",
    "index_catalog_entry",
]
