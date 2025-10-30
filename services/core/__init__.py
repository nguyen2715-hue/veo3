# -*- coding: utf-8 -*-
"""
Core services module - Unified configuration, API management, and key management
"""

from services.core.config import load as load_config, save as save_config
from services.core.key_manager import get_key, refresh as refresh_keys
from services.core.api_config import (
    GEMINI_TEXT_MODEL,
    GEMINI_IMAGE_MODEL,
    gemini_text_endpoint,
    gemini_image_endpoint,
    DEFAULT_TIMEOUT,
    TEXT_GEN_TIMEOUT,
    IMAGE_GEN_TIMEOUT,
    VIDEO_GEN_TIMEOUT,
)

__all__ = [
    'load_config',
    'save_config',
    'get_key',
    'refresh_keys',
    'GEMINI_TEXT_MODEL',
    'GEMINI_IMAGE_MODEL',
    'gemini_text_endpoint',
    'gemini_image_endpoint',
    'DEFAULT_TIMEOUT',
    'TEXT_GEN_TIMEOUT',
    'IMAGE_GEN_TIMEOUT',
    'VIDEO_GEN_TIMEOUT',
]
