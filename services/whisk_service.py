# -*- coding: utf-8 -*-
"""
Whisk Service - Google Labs Image Remix API integration
Correct 3-step workflow from real browser traffic analysis
"""
import requests
import base64
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


# Correct Whisk API endpoints from real browser traffic
WHISK_UPLOAD_ENDPOINT = "https://labs.google/fx/api/trpc/backbone.uploadImage"
WHISK_RECIPE_ENDPOINT = "https://aisandbox-pa.googleapis.com/v1/whisk:runImageRecipe"

# Constants
MAX_REFERENCE_IMAGES = 3  # Whisk supports up to 3 reference images
IMAGE_DOWNLOAD_TIMEOUT = 30  # Timeout for downloading generated image
DEFAULT_GENERATION_TIMEOUT = 90  # Default timeout for image generation


class WhiskError(Exception):
    """Base exception for Whisk service errors"""
    pass


class WhiskClient:
    """Simplified Whisk client using only OAuth token"""
    
    def __init__(self, oauth_tokens: Optional[List[str]] = None, session_tokens: Optional[List[str]] = None):
        """
        Initialize Whisk client
        
        Args:
            oauth_tokens: OAuth tokens from "Google Labs Token" field in Settings
                         (saved as 'labs_tokens' or 'tokens' in config)
            session_tokens: Session tokens for cookie-based upload auth
        """
        self.oauth_tokens = oauth_tokens or []
        self.session_tokens = session_tokens or []
        self._current_token_index = 0
    
    def _get_session_token(self) -> Optional[str]:
        """Get session token from config or init (for cookie-based upload auth)"""
        if self.session_tokens:
            return self.session_tokens[0]
        
        try:
            from utils import config as cfg
            st = cfg.load() or {}
            # Try session_tokens first (new dedicated field)
            tokens = st.get("session_tokens") or []
            if isinstance(tokens, list) and tokens:
                return tokens[0]
        except Exception:
            pass
        
        return None
    
    def _get_oauth_token(self) -> Optional[str]:
        """Get OAuth token from config or init (for Bearer token auth in generation)"""
        if self.oauth_tokens:
            return self.oauth_tokens[0]
        
        try:
            from utils import config as cfg
            st = cfg.load() or {}
            # Use labs_tokens for OAuth (existing field)
            oauth_tokens = st.get("labs_tokens") or st.get("tokens") or []
            if isinstance(oauth_tokens, list) and oauth_tokens:
                return oauth_tokens[0]
        except Exception:
            pass
        
        return None
    
    def upload_image(self, image_path: str, workflow_id: str, session_id: str, debug_callback=None) -> Optional[str]:
        """
        Step 1: Upload image with Session Token
        
        Args:
            image_path: Path to the image file
            workflow_id: Workflow UUID for this generation session
            session_id: Session ID for this generation (format: ;timestamp)
            debug_callback: Optional callback for debug logging
            
        Returns:
            mediaGenerationId for use in recipe
            
        Raises:
            WhiskError: If upload fails
        """
        def _log(msg):
            if debug_callback:
                debug_callback(msg)
            print(msg)  # Always log to console
        
        session_token = self._get_session_token()
        if not session_token:
            _log("[ERROR] No session token available for Whisk upload")
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
        
        # Build raw_bytes in correct format
        raw_bytes = f"data:{mime_type};base64,{image_b64}"
        
        # Upload request with cookie-based auth (correct format from real traffic)
        headers = {
            'Cookie': f'__Secure-next-auth.session-token={session_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "json": {
                "clientContext": {
                    "workflowId": workflow_id,
                    "sessionId": session_id
                },
                "uploadMediaInput": {
                    "mediaCategory": "MEDIA_CATEGORY_SUBJECT",
                    "rawBytes": raw_bytes
                }
            }
        }
        
        try:
            _log(f"[INFO] Whisk: Uploading {Path(image_path).name}...")
            response = requests.post(
                WHISK_UPLOAD_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            _log(f"[INFO] Whisk: Upload response status {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            # Extract mediaGenerationId from response
            media_id = data.get('result', {}).get('data', {}).get('json', {}).get('mediaGenerationId')
            if not media_id:
                _log(f"[ERROR] No mediaGenerationId in upload response")
                raise WhiskError(f"No mediaGenerationId in response: {data}")
            
            _log(f"[SUCCESS] Whisk: Uploaded successfully, got media ID")
            return media_id
            
        except requests.RequestException as e:
            _log(f"[ERROR] Whisk: Upload failed: {e}")
            raise WhiskError(f"Upload request failed: {e}")
    
    def generate_with_media_ids(
        self, 
        prompt: str, 
        media_ids: List[str], 
        workflow_id: str, 
        session_id: str,
        aspect_ratio: str = "9:16",
        timeout: int = DEFAULT_GENERATION_TIMEOUT,
        debug_callback=None
    ) -> Optional[Dict[str, Any]]:
        """
        Step 2: Generate with OAuth Token using uploaded media IDs
        
        Args:
            prompt: User instruction for generation
            media_ids: List of mediaGenerationId from Step 1
            workflow_id: Workflow UUID
            session_id: Session ID
            aspect_ratio: Aspect ratio (e.g., "9:16")
            timeout: Request timeout in seconds
            debug_callback: Optional callback function for debug messages
            
        Returns:
            Dict with imageUrl or None on failure
            
        Raises:
            WhiskError: If generation fails
        """
        def _log(msg):
            if debug_callback:
                debug_callback(msg)
            print(msg)  # Always log to console
        
        # Get OAuth token
        oauth_token = self._get_oauth_token()
        if not oauth_token:
            raise WhiskError("No OAuth token available for Whisk generation")
        
        # Map aspect ratio to Whisk format
        aspect_map = {
            "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
            "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "1:1": "IMAGE_ASPECT_RATIO_SQUARE"
        }
        aspect_value = aspect_map.get(aspect_ratio, "IMAGE_ASPECT_RATIO_PORTRAIT")
        
        # Build recipe inputs from media IDs
        recipe_inputs = [
            {
                "mediaInput": {
                    "mediaGenerationId": mid,
                    "mediaCategory": "MEDIA_CATEGORY_SUBJECT"
                }
            }
            for mid in media_ids
        ]
        
        # Build recipe request (correct format from real traffic)
        headers = {
            'Authorization': f'Bearer {oauth_token}',
            'Content-Type': 'text/plain;charset=UTF-8'
        }
        
        payload = {
            "clientContext": {
                "workflowId": workflow_id,
                "tool": "BACKBONE",
                "sessionId": session_id
            },
            "userInstruction": prompt,
            "recipeMediaInputs": recipe_inputs,
            "imageModelSettings": {
                "imageModel": "R2I",
                "aspectRatio": aspect_value
            }
        }
        
        # Make request
        try:
            _log(f"[INFO] Whisk: Sending generation request with {len(media_ids)} references...")
            response = requests.post(
                WHISK_RECIPE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            _log(f"[INFO] Whisk: Response status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract image URL from response
                if 'generatedImages' in data and data['generatedImages']:
                    _log("[SUCCESS] Whisk: Image generated!")
                    return {"imageUrl": data['generatedImages'][0].get('imageUrl')}
                
                _log(f"[ERROR] No generatedImages in response: {data}")
                raise WhiskError(f"No generatedImages in response: {data}")
            else:
                _log(f"[ERROR] Whisk failed: HTTP {response.status_code}")
                raise WhiskError(f"HTTP {response.status_code}: {response.text[:200]}")
            
        except requests.Timeout:
            _log(f"[ERROR] Whisk timeout after {timeout}s")
            raise WhiskError(f"Timeout after {timeout}s")
        except requests.RequestException as e:
            _log(f"[ERROR] Whisk request failed: {e}")
            raise WhiskError(f"Recipe request failed: {e}")
    
    def generate_with_references(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        aspect_ratio: str = "9:16",
        timeout: int = 120,
        debug_callback=None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete 3-step workflow: Upload → Generate → Result with detailed progress logging
        
        Args:
            prompt: Text prompt for generation
            reference_images: List of paths to reference images (up to 3)
            aspect_ratio: Aspect ratio (e.g., "9:16", "16:9", "1:1")
            timeout: Request timeout in seconds
            debug_callback: Optional callback for debug logging
            
        Returns:
            Dict with imageUrl or None on failure
            
        Raises:
            WhiskError: If generation fails
        """
        def log(msg):
            """Log to both callback and console"""
            print(msg)  # Always print to console
            if debug_callback:
                debug_callback(msg)
        
        try:
            log("[INFO] Whisk: Starting generation...")
            
            # Generate workflow ID and session ID
            workflow_id = str(uuid.uuid4())
            # Session ID format from real traffic: semicolon followed by timestamp in milliseconds
            session_id = f";{int(time.time() * 1000)}"
            
            # Upload reference images
            media_ids = []
            if reference_images:
                log(f"[INFO] Whisk: Uploading {len(reference_images)} reference images...")
                for i, img_path in enumerate(reference_images[:MAX_REFERENCE_IMAGES]):
                    log(f"[INFO] Whisk: Uploading image {i+1}/{len(reference_images[:MAX_REFERENCE_IMAGES])}...")
                    try:
                        media_id = self.upload_image(img_path, workflow_id, session_id, debug_callback=debug_callback)
                        if media_id:
                            media_ids.append(media_id)
                            log(f"[SUCCESS] Whisk: Uploaded {Path(img_path).name}")
                        else:
                            log(f"[ERROR] Whisk: Upload failed for {Path(img_path).name}")
                    except Exception as e:
                        log(f"[ERROR] Whisk: Upload error - {str(e)[:100]}")
            
            if not media_ids:
                log("[ERROR] Whisk: No images uploaded successfully")
                raise WhiskError("No images uploaded")
            
            log(f"[INFO] Whisk: Generating image with {len(media_ids)} references...")
            
            # Generate with timeout
            result = self.generate_with_media_ids(
                prompt, media_ids, workflow_id, session_id,
                aspect_ratio=aspect_ratio, timeout=timeout, debug_callback=debug_callback
            )
            
            if result and result.get("imageUrl"):
                log("[SUCCESS] Whisk: Image generated successfully!")
                return result
            else:
                log("[ERROR] Whisk: No image URL in response")
                raise WhiskError("No image URL in response")
                
        except requests.Timeout:
            log(f"[ERROR] Whisk: Request timeout after {timeout}s")
            raise WhiskError(f"Timeout after {timeout}s")
        except Exception as e:
            log(f"[ERROR] Whisk: Generation failed - {str(e)[:150]}")
            raise WhiskError(str(e))



# Simplified interface function for backward compatibility
def generate_image(
    prompt: str,
    model_image: Optional[str] = None,
    product_image: Optional[str] = None,
    timeout: int = 90,
    debug_callback=None
) -> bytes:
    """
    Simplified interface for generating images with model and product references
    Uses WhiskClient 3-step workflow with auto-fallback to Gemini on failure
    
    Args:
        prompt: Text prompt for image generation
        model_image: Path to model/person reference image
        product_image: Path to product reference image
        timeout: Request timeout in seconds
        debug_callback: Optional callback for debug logging
        
    Returns:
        Generated image as bytes
        
    Raises:
        WhiskError: If both Whisk and Gemini fail
    """
    # Try Whisk 3-step workflow first
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
            timeout=timeout,
            debug_callback=debug_callback
        )
        
        # Step 3: Download image
        if result and result.get("imageUrl"):
            img_response = requests.get(result["imageUrl"], timeout=IMAGE_DOWNLOAD_TIMEOUT)
            img_response.raise_for_status()
            return img_response.content
        
        raise WhiskError("No imageUrl in result")
        
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
