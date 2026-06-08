"""Research playbooks distilled from broker reports."""

from .registry import get_playbook, list_playbooks, resolve_playbook_stack
from ..symbol_parse import product_id_from_symbol

__all__ = [
    "get_playbook",
    "list_playbooks",
    "product_id_from_symbol",
    "resolve_playbook_stack",
]
