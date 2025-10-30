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


def generate_image_gemini(prompt: str, timeout: int = 120, retry_delay: float = 2.5, log_callback=None) -> bytes:
    """
    Generate image using Gemini/Imagen API with enhanced debug logging
    
    Args:
        prompt: Text prompt for image generation
        timeout: Request timeout in seconds
        retry_delay: Delay between retries (for rate limiting)
        log_callback: Optional callback function for logging (receives string messages)
        
    Returns:
        Generated image as bytes
        
    Raises:
        ImageGenError: If generation fails
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
    
    keys = _google_keys()
    if not keys:
        raise ImageGenError("No Google API keys available")
    
    log(f"[DEBUG] Tìm thấy {len(keys)} Google API keys")
    
    # Try each key with retry logic
    last_error = None
    for key_idx, api_key in enumerate(keys):
        try:
            key_preview = f"...{api_key[-6:]}" if len(api_key) > 6 else "***"
            log(f"[INFO] Key {key_preview} (lần {key_idx + 1})")
            
            # Gemini image generation endpoint with correct model
            # Using gemini-2.5-flash-image model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseModalities": ["image"]
                }
            }
            
            response = requests.post(url, json=payload, timeout=timeout)
            
            log(f"[DEBUG] HTTP {response.status_code}")
            
            # Handle rate limiting
            if response.status_code == 429:
                log(f"[WARNING] Rate limit 429 on key {key_preview}")
                if key_idx < len(keys) - 1:
                    # Try next key after delay
                    time.sleep(retry_delay)
                    continue
                else:
                    raise ImageGenError("Rate limit exceeded on all keys")
            
            # Parse error responses
            if response.status_code != 200:
                try:
                    error_body = response.json()
                    error_msg = error_body.get("error", {}).get("message", str(error_body))
                    log(f"[ERROR] API Error {response.status_code}: {error_msg[:150]}")
                except:
                    log(f"[ERROR] HTTP {response.status_code}: {response.text[:150]}")
            
            response.raise_for_status()
            data = response.json()
            
            log(f"[DEBUG] Response keys: {list(data.keys())}")
            
            # Extract image data from Gemini generateContent response
            if 'candidates' in data and data['candidates']:
                log(f"[DEBUG] Candidates count: {len(data['candidates'])}")
                candidate = data['candidates'][0]
                
                # Check for inline data in parts
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                
                for part in parts:
                    if 'inlineData' in part:
                        inline_data = part['inlineData']
                        if 'data' in inline_data:
                            img_data = base64.b64decode(inline_data['data'])
                            log(f"[SUCCESS] Tạo ảnh thành công ({len(img_data)} bytes)")
                            return img_data
            
            log(f"[ERROR] No image data in response: {data}")
            raise ImageGenError(f"No image data in response: {data}")
            
        except requests.RequestException as e:
            log(f"[ERROR] Request exception: {str(e)[:100]}")
            last_error = e
            if key_idx < len(keys) - 1:
                time.sleep(retry_delay)
                continue
    
    if last_error:
        raise ImageGenError(f"Image generation failed: {last_error}")
    raise ImageGenError("Image generation failed with all keys")


def generate_image_with_rate_limit(prompt: str, delay: float = 2.5, log_callback=None) -> Optional[bytes]:
    """
    Generate image with automatic rate limiting delay
    
    Args:
        prompt: Text prompt
        delay: Delay in seconds before generation (to avoid rate limits)
        log_callback: Optional callback function for logging
        
    Returns:
        Image bytes or None if failed
    """
    if delay > 0:
        time.sleep(delay)
    try:
        return generate_image_gemini(prompt, log_callback=log_callback)
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Generation failed: {str(e)[:100]}")
        return None
