# -*- coding: utf-8 -*-
"""
Whisk Service - Google Labs Image Remix API integration
Correct endpoints from real browser traffic
"""
import requests
import time
import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path


# Correct Whisk API endpoints
WHISK_UPLOAD_ENDPOINT = "https://labs.google/fx/api/trpc/backbone.uploadImage"
WHISK_RECIPE_ENDPOINT = "https://aisandbox-pa.googleapis.com/v1/whisk:runImageRecipe"


class WhiskError(Exception):
    """Base exception for Whisk service errors"""
    pass


class WhiskClient:
    """Whisk API client with correct endpoints and authentication"""
    
    def __init__(self, session_tokens: Optional[List[str]] = None, oauth_tokens: Optional[List[str]] = None):
        """
        Initialize Whisk client
        
        Args:
            session_tokens: List of session tokens from cookies (__Secure-next-auth.session-token)
            oauth_tokens: List of OAuth tokens from Authorization headers (ya29...)
        """
        self.session_tokens = session_tokens or []
        self.oauth_tokens = oauth_tokens or []
    
    def _get_session_token(self) -> Optional[str]:
        """Get session token from config or init"""
        if self.session_tokens:
            return self.session_tokens[0]
        
        try:
            from utils import config as cfg
            st = cfg.load() or {}
            tokens = st.get("tokens") or []
            if isinstance(tokens, list) and tokens:
                return tokens[0]
        except Exception:
            pass
        
        return None
    
    def _get_oauth_token(self) -> Optional[str]:
        """Get OAuth token from config or init"""
        if self.oauth_tokens:
            return self.oauth_tokens[0]
        
        try:
            from utils import config as cfg
            st = cfg.load() or {}
            oauth_tokens = st.get("oauth_tokens") or []
            if isinstance(oauth_tokens, list) and oauth_tokens:
                return oauth_tokens[0]
        except Exception:
            pass
        
        return None
    
    def upload_image(self, image_path: str) -> str:
        """
        Upload an image file to Whisk upload endpoint
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Upload ID/token for use in recipe
            
        Raises:
            WhiskError: If upload fails
        """
        session_token = self._get_session_token()
        if not session_token:
            raise WhiskError("No session token available for Whisk upload")
        
        # Read image file
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            raise WhiskError(f"Failed to read image file: {e}")
        
        # Encode to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Determine mime type
        ext = Path(image_path).suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }
        mime_type = mime_map.get(ext, 'image/jpeg')
        
        # Upload request with cookie-based auth
        headers = {
            'Cookie': f'__Secure-next-auth.session-token={session_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'image': image_b64,
            'mimeType': mime_type
        }
        
        try:
            response = requests.post(
                WHISK_UPLOAD_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract upload ID from response
            upload_id = data.get('result', {}).get('data', {}).get('uploadId')
            if not upload_id:
                raise WhiskError(f"No uploadId in response: {data}")
                
            return upload_id
            
        except requests.RequestException as e:
            raise WhiskError(f"Upload request failed: {e}")
    
    def generate_with_references(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "9:16",
        timeout: int = 120
    ) -> bytes:
        """
        Generate image using Whisk recipe endpoint with reference images
        
        Args:
            prompt: Text prompt for generation
            reference_images: List of paths to reference images (model, product, etc.)
            aspect_ratio: Aspect ratio (e.g., "9:16", "16:9", "1:1")
            timeout: Request timeout in seconds
            
        Returns:
            Generated image as bytes
            
        Raises:
            WhiskError: If generation fails
        """
        oauth_token = self._get_oauth_token()
        if not oauth_token:
            raise WhiskError("No OAuth token available for Whisk recipe")
        
        # Upload reference images
        uploaded_refs = []
        if reference_images:
            for img_path in reference_images:
                try:
                    upload_id = self.upload_image(img_path)
                    uploaded_refs.append(upload_id)
                except Exception as e:
                    raise WhiskError(f"Failed to upload reference image: {e}")
        
        # Build recipe request (REMOVED invalid imageModel parameter)
        headers = {
            'Authorization': f'Bearer {oauth_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'prompt': prompt,
            'aspectRatio': aspect_ratio,
            'references': uploaded_refs
        }
        
        try:
            response = requests.post(
                WHISK_RECIPE_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract image URL or data from response
            if 'imageUrl' in data:
                image_url = data['imageUrl']
                img_response = requests.get(image_url, timeout=60)
                img_response.raise_for_status()
                return img_response.content
            
            if 'imageData' in data:
                return base64.b64decode(data['imageData'])
                
            raise WhiskError(f"No image data in response: {data}")
            
        except requests.RequestException as e:
            raise WhiskError(f"Recipe request failed: {e}")


# Legacy/simplified interface functions

def generate_image(
    prompt: str,
    model_image: Optional[str] = None,
    product_image: Optional[str] = None,
    timeout: int = 120
) -> bytes:
    """
    Simplified interface for generating images with model and product references
    Uses WhiskClient with auto-fallback to Gemini on failure
    
    Args:
        prompt: Text prompt for image generation
        model_image: Path to model/person reference image
        product_image: Path to product reference image
        timeout: Request timeout in seconds
        
    Returns:
        Generated image as bytes
        
    Raises:
        WhiskError: If generation fails
    """
    # Try Whisk first
    try:
        client = WhiskClient()
        reference_images = []
        if model_image:
            reference_images.append(model_image)
        if product_image:
            reference_images.append(product_image)
        
        return client.generate_with_references(
            prompt=prompt,
            reference_images=reference_images if reference_images else None,
            timeout=timeout
        )
    except Exception as whisk_error:
        # Auto-fallback to Gemini
        try:
            from services import image_gen_service
            img_data = image_gen_service.generate_image_gemini(prompt, timeout)
            if img_data:
                return img_data
        except Exception as gemini_error:
            raise WhiskError(f"Whisk failed: {whisk_error}. Gemini fallback failed: {gemini_error}")
