# -*- coding: utf-8 -*-
"""
Legacy key manager - Now delegates to services.core.key_manager
Kept for backward compatibility
"""
import threading
from typing import List, Dict

# Import from unified core
from services.core.key_manager import (
    refresh as core_refresh,
    get_key as core_get_key,
    get_all_keys as core_get_all_keys,
    rotated_list as core_rotated_list
)


# Backward compatibility aliases
def refresh():
    """Refresh key pools (delegates to core)"""
    core_refresh()
    return {}  # Legacy return value


def take(provider: str) -> str:
    """Take next key from provider (delegates to core)"""
    return core_get_key(provider)


def rotated_list(provider: str, base: list) -> list:
    """Get rotated list (delegates to core)"""
    return core_rotated_list(provider, base)
