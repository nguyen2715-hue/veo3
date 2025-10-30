# -*- coding: utf-8 -*-
"""
Whisk Service - Google Labs Image Remix API integration
"""
import requests
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


WHISK_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class WhiskError(Exception):
    """Base exception for Whisk service errors"""
    pass


def _get_api_key() -> str:
    """Get Google API key from config"""
    try:
        from utils import config as cfg
        st = cfg.load() or {}
        keys = st.get("google_api_keys") or []
        if isinstance(keys, list) and keys:
            return keys[0]
        key = st.get("google_api_key")
        if key:
            return key
        raise WhiskError("No Google API key found in config")
    except Exception as e:
        raise WhiskError(f"Failed to get API key: {e}")


def upload_image_file(image_path: str) -> str:
    """
    Upload an image file to Google's media generation service
    
    Args:
        image_path: Path to the image file
        
    Returns:
        mediaGenerationId string for use in recipe
        
    Raises:
        WhiskError: If upload fails
    """
    api_key = _get_api_key()
    
    # Read image file
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
    except Exception as e:
        raise WhiskError(f"Failed to read image file: {e}")
    
    # Determine mime type
    ext = Path(image_path).suffix.lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp'
    }
    mime_type = mime_map.get(ext, 'image/jpeg')
    
    # Upload to media generation endpoint
    url = f"{WHISK_API_BASE}/media:upload?key={api_key}"
    
    try:
        response = requests.post(
            url,
            files={'file': (Path(image_path).name, image_data, mime_type)},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        
        media_id = data.get('mediaGenerationId')
        if not media_id:
            raise WhiskError(f"No mediaGenerationId in response: {data}")
            
        return media_id
        
    except requests.RequestException as e:
        raise WhiskError(f"Upload request failed: {e}")


def generate_with_references(
    prompt: str,
    subject_image_path: Optional[str] = None,
    style_image_path: Optional[str] = None,
    scene_image_path: Optional[str] = None,
    timeout: int = 120
) -> bytes:
    """
    Generate image using Whisk (Image Remix) with reference images
    
    Args:
        prompt: Text prompt for generation
        subject_image_path: Path to subject/model reference image
        style_image_path: Path to style reference image
        scene_image_path: Path to scene/product reference image
        timeout: Request timeout in seconds
        
    Returns:
        Generated image as bytes
        
    Raises:
        WhiskError: If generation fails
    """
    api_key = _get_api_key()
    
    # Upload reference images
    recipe_inputs = {}
    
    if subject_image_path:
        try:
            subject_id = upload_image_file(subject_image_path)
            recipe_inputs['subject'] = {'mediaGenerationId': subject_id}
        except Exception as e:
            raise WhiskError(f"Failed to upload subject image: {e}")
    
    if style_image_path:
        try:
            style_id = upload_image_file(style_image_path)
            recipe_inputs['style'] = {'mediaGenerationId': style_id}
        except Exception as e:
            raise WhiskError(f"Failed to upload style image: {e}")
            
    if scene_image_path:
        try:
            scene_id = upload_image_file(scene_image_path)
            recipe_inputs['scene'] = {'mediaGenerationId': scene_id}
        except Exception as e:
            raise WhiskError(f"Failed to upload scene image: {e}")
    
    # Call runImageRecipe
    url = f"{WHISK_API_BASE}/models/image-remix:runImageRecipe?key={api_key}"
    
    payload = {
        "recipeMediaInputs": recipe_inputs,
        "prompt": prompt
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract image URL or data from response
        # The actual response format may vary - adjust as needed
        if 'image' in data:
            image_url = data['image'].get('url')
            if image_url:
                # Download the image
                img_response = requests.get(image_url, timeout=60)
                img_response.raise_for_status()
                return img_response.content
        
        # Alternative: check for inline image data
        if 'imageData' in data:
            import base64
            return base64.b64decode(data['imageData'])
            
        raise WhiskError(f"No image data in response: {data}")
        
    except requests.RequestException as e:
        raise WhiskError(f"Recipe request failed: {e}")


def generate_image(
    prompt: str,
    model_image: Optional[str] = None,
    product_image: Optional[str] = None,
    timeout: int = 120
) -> bytes:
    """
    Simplified interface for generating images with model and product references
    
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
    return generate_with_references(
        prompt=prompt,
        subject_image_path=model_image,
        scene_image_path=product_image,
        timeout=timeout
    )
