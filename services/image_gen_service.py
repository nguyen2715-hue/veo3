# -*- coding: utf-8 -*-
import os, base64, json, requests, mimetypes, uuid, time
from typing import Optional, Dict, Any
from services.core.api_config import GEMINI_IMAGE_MODEL, gemini_image_endpoint, IMAGE_GEN_TIMEOUT
from services.core.key_manager import get_all_keys, refresh


class ImageGenError(Exception):
    """Image generation error"""
    pass


def generate_image_gemini(prompt: str, timeout: int = None, retry_delay: float = 2.5, log_callback=None) -> bytes:
    """
    Generate image using Gemini Flash Image model with enhanced debug logging
    
    Args:
        prompt: Text prompt for image generation
        timeout: Request timeout in seconds (default from api_config)
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
    
    timeout = timeout or IMAGE_GEN_TIMEOUT
    refresh()  # Refresh key pool
    keys = get_all_keys('google')
    if not keys:
        raise ImageGenError("No Google API keys available")
    
    log(f"[DEBUG] Tìm thấy {len(keys)} Google API keys")
    
    # Try each key with retry logic
    last_error = None
    for key_idx, api_key in enumerate(keys):
        try:
            key_preview = f"...{api_key[-6:]}" if len(api_key) > 6 else "***"
            log(f"[INFO] Key {key_preview} (lần {key_idx + 1})")
            
            # FIXED: Use correct Gemini Flash Image model and endpoint
            url = gemini_image_endpoint(api_key)
            
            # Correct payload format for Gemini Flash Image
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 1.0,
                    "maxOutputTokens": 8192
                }
            }
            
            response = requests.post(url, json=payload, timeout=timeout)
            
            log(f"[DEBUG] HTTP {response.status_code}")
            
            # Handle rate limiting - skip to next key immediately (don't wait)
            if response.status_code == 429:
                log(f"[WARNING] Key {key_preview} rate limited, trying next key...")
                
                # Skip to next key immediately (don't wait)
                if key_idx < len(keys) - 1:
                    continue  # Try next key now!
                else:
                    log("[ERROR] All API keys are rate limited!")
                    # Get retry-after for last key
                    try:
                        retry_after = int(response.headers.get('Retry-After', 60))
                    except (ValueError, TypeError):
                        retry_after = 60  # Fallback if header is invalid
                    log(f"[INFO] Waiting {retry_after}s before final retry...")
                    time.sleep(retry_after)
                    # One final retry with first key
                    response = requests.post(gemini_image_endpoint(keys[0]), json=payload, timeout=timeout)
                    if response.status_code == 200:
                        # Success after wait - continue to image extraction below
                        log("[SUCCESS] Final retry succeeded")
                    else:
                        raise ImageGenError("All API keys exhausted quota")
            
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
            
            # Extract image data from Gemini Flash Image response format
            if 'candidates' in data and data['candidates']:
                log(f"[DEBUG] Candidates count: {len(data['candidates'])}")
                candidate = data['candidates'][0]
                parts = candidate.get('content', {}).get('parts', [])
                
                for part in parts:
                    if 'inlineData' in part:
                        img_b64 = part['inlineData']['data']
                        img_data = base64.b64decode(img_b64)
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


def generate_image_with_rate_limit(prompt: str, delay: float = 8.0, log_callback=None) -> Optional[bytes]:
    """
    Generate image with automatic rate limiting delay
    
    Args:
        prompt: Text prompt
        delay: Delay in seconds before generation (default 8.0s for 15 req/min limit)
               Safe delay: 60s / 15 requests = 4s min, use 8s to be safe
        log_callback: Optional callback function for logging
        
    Returns:
        Image bytes or None if failed
    """
    if delay > 0:
        if log_callback:
            log_callback(f"[INFO] Waiting {delay}s for rate limit...")
        time.sleep(delay)
    try:
        return generate_image_gemini(prompt, log_callback=log_callback)
    except Exception as e:
        # Check if rate limited
        if '429' in str(e) or 'rate limit' in str(e).lower():
            if log_callback:
                log_callback(f"[WARNING] Rate limited, waiting 60s...")
            time.sleep(60)  # Wait 1 minute before retry
            try:
                return generate_image_gemini(prompt, log_callback=log_callback)
            except Exception as retry_error:
                if log_callback:
                    log_callback(f"[ERROR] Retry failed: {str(retry_error)[:100]}")
                return None
        if log_callback:
            log_callback(f"[ERROR] Generation failed: {str(e)[:100]}")
        return None
