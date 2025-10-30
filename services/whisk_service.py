# -*- coding: utf-8 -*-
"""
Whisk Service - Simplified OAuth-only implementation
Based on real Google Labs browser traffic analysis
"""
import requests
import base64
import os
from typing import Dict, Any, List, Optional


# Whisk API endpoint (OAuth-only, no upload needed)
WHISK_RECIPE_ENDPOINT = "https://aisandbox-pa.googleapis.com/v1/whisk:runImageRecipe"


class WhiskError(Exception):
    """Base exception for Whisk service errors"""
    pass


class WhiskClient:
    """Simplified Whisk client using only OAuth token"""
    
    def __init__(self, oauth_tokens: Optional[List[str]] = None):
        """
        Initialize Whisk client
        
        Args:
            oauth_tokens: OAuth tokens from "Google Labs Token" field in Settings
                         (saved as 'labs_tokens' or 'tokens' in config)
        """
        self.oauth_tokens = oauth_tokens or []
        self._current_token_index = 0
    
    def _get_next_token(self) -> Optional[str]:
        """Get next OAuth token from list (with rotation)"""
        if not self.oauth_tokens:
            # Try to load from config if not provided in init
            try:
                from utils import config as cfg
                st = cfg.load() or {}
                # Check both 'labs_tokens' and 'tokens' (Settings saves to both)
                self.oauth_tokens = st.get("labs_tokens") or st.get("tokens") or []
            except Exception:
                pass
        
        if not self.oauth_tokens:
            return None
        
        token = self.oauth_tokens[self._current_token_index % len(self.oauth_tokens)]
        self._current_token_index += 1
        return token
    
    def generate_with_references(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "9:16",
        timeout: int = 90,
        debug_callback=None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate image directly with OAuth token (no upload step needed)
        
        Process:
        1. Encode reference images to base64
        2. POST to whisk:runImageRecipe with OAuth token
        3. Return response with imageUrl or imageData
        
        Args:
            prompt: Text prompt for generation
            reference_images: List of paths to reference images (up to 3)
            aspect_ratio: "9:16" (PORTRAIT) or "16:9" (LANDSCAPE)
            timeout: Request timeout in seconds
            debug_callback: Optional callback function for debug messages
            
        Returns:
            Response dict with 'imageUrl' or 'imageData' key, or None on failure
        """
        def _log(msg):
            if debug_callback:
                debug_callback(msg)
        
        # Get OAuth token
        oauth_token = self._get_next_token()
        if not oauth_token:
            _log("[ERROR] No OAuth token available")
            return None
        
        # Encode reference images to base64
        image_data_list = []
        if reference_images:
            for img_path in reference_images[:3]:  # Limit to 3 images
                try:
                    with open(img_path, 'rb') as f:
                        img_bytes = f.read()
                    
                    # Determine mime type
                    ext = os.path.splitext(img_path)[1].lower()
                    mime_type = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.webp': 'image/webp'
                    }.get(ext, 'image/jpeg')
                    
                    # Encode to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    image_data_list.append({
                        "mimeType": mime_type,
                        "data": img_base64
                    })
                    _log(f"[DEBUG] Encoded reference image: {os.path.basename(img_path)}")
                except Exception as e:
                    _log(f"[WARN] Failed to encode image {img_path}: {e}")
                    continue
        
        # Build request payload
        aspect_map = {
            "9:16": "PORTRAIT",
            "16:9": "LANDSCAPE",
            "1:1": "SQUARE"
        }
        
        payload = {
            "prompt": prompt[:500],  # Limit prompt length
            "aspectRatio": aspect_map.get(aspect_ratio, "PORTRAIT"),
            "referenceImages": image_data_list,
            "numResults": 1
        }
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        }
        
        # Make request
        try:
            _log(f"[DEBUG] Sending Whisk request with {len(image_data_list)} references...")
            response = requests.post(
                WHISK_RECIPE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                _log(f"[DEBUG] Whisk success! Response keys: {list(result.keys())}")
                return self._parse_image_response(result, _log)
            elif response.status_code in (401, 403):
                _log(f"[ERROR] OAuth token expired or invalid ({response.status_code})")
                return None
            else:
                _log(f"[ERROR] Whisk API error: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.Timeout:
            _log(f"[ERROR] Whisk request timeout after {timeout}s")
            return None
        except Exception as e:
            _log(f"[ERROR] Whisk request failed: {e}")
            return None
    
    def _parse_image_response(self, result: Dict[str, Any], _log) -> Optional[Dict[str, Any]]:
        """Parse image URL or data from Whisk response"""
        # Check for imageUrl (direct URL to generated image)
        if "imageUrl" in result:
            _log("[SUCCESS] Got image URL from Whisk")
            return {"imageUrl": result["imageUrl"]}
        
        # Check for imageData (base64 encoded)
        if "imageData" in result:
            _log("[SUCCESS] Got base64 image data from Whisk")
            return {"imageData": result["imageData"]}
        
        # Check for nested results (generatedImages array)
        if "generatedImages" in result and isinstance(result["generatedImages"], list):
            if len(result["generatedImages"]) > 0:
                first_img = result["generatedImages"][0]
                if "imageUrl" in first_img:
                    _log("[SUCCESS] Got image URL from generatedImages[0]")
                    return {"imageUrl": first_img["imageUrl"]}
                if "imageData" in first_img:
                    _log("[SUCCESS] Got image data from generatedImages[0]")
                    return {"imageData": first_img["imageData"]}
        
        _log(f"[ERROR] No image data in Whisk response: {list(result.keys())}")
        return None



# Simplified interface function for backward compatibility
def generate_image(
    prompt: str,
    model_image: Optional[str] = None,
    product_image: Optional[str] = None,
    timeout: int = 90
) -> bytes:
    """
    Simplified interface for generating images with model and product references
    Uses simplified OAuth-only WhiskClient with auto-fallback to Gemini on failure
    
    Args:
        prompt: Text prompt for image generation
        model_image: Path to model/person reference image
        product_image: Path to product reference image
        timeout: Request timeout in seconds
        
    Returns:
        Generated image as bytes
        
    Raises:
        WhiskError: If both Whisk and Gemini fail
    """
    # Try Whisk first with OAuth-only approach
    try:
        client = WhiskClient()
        reference_images = []
        if model_image:
            reference_images.append(model_image)
        if product_image:
            reference_images.append(product_image)
        
        result = client.generate_with_references(
            prompt=prompt,
            reference_images=reference_images if reference_images else None,
            timeout=timeout
        )
        
        if result:
            # Download image from URL
            if "imageUrl" in result:
                img_response = requests.get(result["imageUrl"], timeout=60)
                img_response.raise_for_status()
                return img_response.content
            
            # Decode base64 image data
            if "imageData" in result:
                return base64.b64decode(result["imageData"])
        
        # If no result, fall through to Gemini
        raise WhiskError("No image data returned from Whisk")
        
    except Exception as whisk_error:
        # Auto-fallback to Gemini
        try:
            from services import image_gen_service
            img_data = image_gen_service.generate_image_gemini(prompt, timeout)
            if img_data:
                return img_data
            raise WhiskError(f"Gemini returned no data")
        except Exception as gemini_error:
            raise WhiskError(f"Whisk failed: {whisk_error}. Gemini fallback failed: {gemini_error}")
