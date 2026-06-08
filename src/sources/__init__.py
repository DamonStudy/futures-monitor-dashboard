"""External data sources — fetch only, no analyzer/skill logic."""

from .context import BatchContext, build_batch_context

__all__ = ["BatchContext", "build_batch_context"]
