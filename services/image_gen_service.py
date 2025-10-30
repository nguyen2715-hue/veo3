# -*- coding: utf-8 -*-
import os, base64, json, requests, mimetypes, uuid, time
from typing import Optional, Dict, Any


def _cfg():
    try:
        from utils import config as cfg
        return cfg.load() if hasattr(cfg, "load") else {}
    except Exception:
        return {}


def _google_keys():
    from services.keys_manager import refresh, rotated_list
    c=_cfg(); refresh()
    out=[]
    # prefer list field
    out += [k for k in (c.get("google_api_keys") or []) if k]
    # legacy single
    if c.get("google_api_key"): out.append(c["google_api_key"])
    # legacy mixed store
    for t in (c.get("tokens") or []):
        if isinstance(t, dict) and t.get("kind") in ("gemini","google"):
            v=t.get("token") or t.get("value")
            if v: out.append(v)
    # de-dup preserve order
    seen=set(); out2=[]
    for k in out:
        if k and (k not in seen):
            out2.append(k); seen.add(k)
    return rotated_list('google', out2)


class ImageGenError(Exception):
    """Image generation error"""
    pass


def generate_image_gemini(prompt: str, timeout: int = 120, retry_delay: float = 2.5) -> bytes:
    """
    Generate image using Gemini/Imagen API
    
    Args:
        prompt: Text prompt for image generation
        timeout: Request timeout in seconds
        retry_delay: Delay between retries (for rate limiting)
        
    Returns:
        Generated image as bytes
        
    Raises:
        ImageGenError: If generation fails
    """
    keys = _google_keys()
    if not keys:
        raise ImageGenError("No Google API keys available")
    
    # Try each key with retry logic
    last_error = None
    for key_idx, api_key in enumerate(keys):
        try:
            # Gemini Imagen endpoint (simplified - may need adjustment)
            # Using the generateImages endpoint from Vertex AI or similar
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={api_key}"
            
            payload = {
                "instances": [
                    {
                        "prompt": prompt
                    }
                ],
                "parameters": {
                    "sampleCount": 1
                }
            }
            
            response = requests.post(url, json=payload, timeout=timeout)
            
            # Handle rate limiting
            if response.status_code == 429:
                if key_idx < len(keys) - 1:
                    # Try next key after delay
                    time.sleep(retry_delay)
                    continue
                else:
                    raise ImageGenError("Rate limit exceeded on all keys")
            
            response.raise_for_status()
            data = response.json()
            
            # Extract image data
            if 'predictions' in data and data['predictions']:
                pred = data['predictions'][0]
                if 'bytesBase64Encoded' in pred:
                    img_data = base64.b64decode(pred['bytesBase64Encoded'])
                    return img_data
                elif 'image' in pred:
                    # Handle other response formats
                    img_data = base64.b64decode(pred['image'])
                    return img_data
            
            raise ImageGenError(f"No image data in response: {data}")
            
        except requests.RequestException as e:
            last_error = e
            if key_idx < len(keys) - 1:
                time.sleep(retry_delay)
                continue
    
    if last_error:
        raise ImageGenError(f"Image generation failed: {last_error}")
    raise ImageGenError("Image generation failed with all keys")


def generate_image_with_rate_limit(prompt: str, delay: float = 2.5) -> Optional[bytes]:
    """
    Generate image with automatic rate limiting delay
    
    Args:
        prompt: Text prompt
        delay: Delay in seconds before generation (to avoid rate limits)
        
    Returns:
        Image bytes or None if failed
    """
    time.sleep(delay)
    try:
        return generate_image_gemini(prompt)
    except Exception:
        return None
