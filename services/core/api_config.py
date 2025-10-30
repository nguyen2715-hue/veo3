# -*- coding: utf-8 -*-
"""
API Configuration - Single Source of Truth for all API models and endpoints
"""

# Models
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"  # FIXED: was "imagen-3.0-generate-001"

# Base URLs
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
WHISK_BASE = "https://labs.google/fx/api/trpc"
LABS_BASE = "https://aisandbox-pa.googleapis.com"

# Timeouts (in seconds)
DEFAULT_TIMEOUT = 120
TEXT_GEN_TIMEOUT = 180
IMAGE_GEN_TIMEOUT = 180
VIDEO_GEN_TIMEOUT = 300


def gemini_text_endpoint(key: str) -> str:
    """
    Get Gemini text generation endpoint
    
    Args:
        key: Google API key
        
    Returns:
        Full endpoint URL with API key
    """
    return f"{GEMINI_BASE}/models/{GEMINI_TEXT_MODEL}:generateContent?key={key}"


def gemini_image_endpoint(key: str) -> str:
    """
    Get Gemini image generation endpoint
    
    Args:
        key: Google API key
        
    Returns:
        Full endpoint URL with API key
    """
    return f"{GEMINI_BASE}/models/{GEMINI_IMAGE_MODEL}:generateContent?key={key}"
