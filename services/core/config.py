# -*- coding: utf-8 -*-
"""
Unified Configuration Loader - Single source for all configuration loading
Replaces all duplicate _cfg() implementations across services
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

CFG_PATH = Path.home() / ".veo_image2video_cfg.json"
_CACHE: Optional[Dict[str, Any]] = None


def load(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from file (cached for performance)
    
    Args:
        force_reload: If True, bypass cache and reload from disk
        
    Returns:
        Configuration dictionary
    """
    global _CACHE
    
    if _CACHE is not None and not force_reload:
        return _CACHE
    
    if CFG_PATH.exists():
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
                return _CACHE
        except Exception:
            # If file is corrupted, return default config
            pass
    
    # Default configuration
    _CACHE = {
        "google_api_keys": [],
        "labs_tokens": [],
        "download_root": str(Path.home() / "Downloads")
    }
    return _CACHE


def save(cfg: Dict[str, Any]) -> bool:
    """
    Save configuration to file (atomic write)
    
    Args:
        cfg: Configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    global _CACHE
    
    try:
        # Atomic write using temporary file
        temp_path = CFG_PATH.with_suffix('.tmp')
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        
        # Rename is atomic on most filesystems
        temp_path.replace(CFG_PATH)
        
        # Update cache
        _CACHE = cfg
        return True
    except Exception:
        return False


def clear_cache():
    """Clear the configuration cache (useful for testing)"""
    global _CACHE
    _CACHE = None
