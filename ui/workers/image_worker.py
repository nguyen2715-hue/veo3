# -*- coding: utf-8 -*-
"""
Image Worker - Non-blocking image generation using QThread
Supports both Gemini and Whisk models
"""
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Any, List
import tempfile
import os

# Import services at module level for better error handling
try:
    from services import image_gen_service
    from services import sales_script_service as sscript
except ImportError as e:
    image_gen_service = None
    sscript = None
    _import_error = str(e)


class ImageWorker(QThread):
    """Worker thread for generating images without blocking the UI"""
    
    # Signals
    progress = pyqtSignal(str)  # Log message
    scene_image_ready = pyqtSignal(int, bytes)  # scene_index, image_data
    thumbnail_ready = pyqtSignal(int, bytes)  # version_index, image_data
    finished = pyqtSignal(bool)  # success
    
    def __init__(self, outline: Dict[str, Any], cfg: Dict[str, Any], 
                 model_paths: List[str], prod_paths: List[str], 
                 use_whisk: bool = False, parent=None):
        """
        Initialize image worker
        
        Args:
            outline: Script outline with scenes
            cfg: Configuration dictionary
            model_paths: List of model image paths
            prod_paths: List of product image paths
            use_whisk: Whether to use Whisk model (True) or Gemini (False)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.outline = outline
        self.cfg = cfg
        self.model_paths = model_paths
        self.prod_paths = prod_paths
        self.use_whisk = use_whisk
        self.should_stop = False
    
    def run(self):
        """Run image generation in background thread"""
        try:
            # Check if service imports were successful
            if image_gen_service is None or sscript is None:
                raise ImportError(f"Failed to import required services: {_import_error}")
            
            # Generate scene images
            scenes = self.outline.get("scenes", [])
            for i, scene in enumerate(scenes):
                if self.should_stop:
                    break
                    
                self.progress.emit(f"Tạo ảnh cảnh {scene.get('index')}...")
                
                # Get prompt
                prompt = scene.get("prompt_image", "")
                
                # Try to generate image
                img_data = None
                if self.use_whisk and self.model_paths and self.prod_paths:
                    # Try Whisk first
                    try:
                        from services import whisk_service
                        img_data = whisk_service.generate_image(
                            prompt=prompt,
                            model_image=self.model_paths[0] if self.model_paths else None,
                            product_image=self.prod_paths[0] if self.prod_paths else None
                        )
                        self.progress.emit(f"Cảnh {scene.get('index')}: Dùng Whisk ✓")
                    except Exception as e:
                        self.progress.emit(f"Whisk failed: {e}, fallback to Gemini...")
                        img_data = None
                
                # Fallback to Gemini or if Whisk not enabled
                if img_data is None:
                    try:
                        # Use Gemini image generation with rate limiting
                        delay = 2.5 if i > 0 else 0
                        self.progress.emit(f"Cảnh {scene.get('index')}: Dùng Gemini...")
                        
                        # Pass log callback for enhanced debug output
                        img_data = image_gen_service.generate_image_with_rate_limit(
                            prompt, 
                            delay, 
                            log_callback=lambda msg: self.progress.emit(msg)
                        )
                        
                        if img_data:
                            self.progress.emit(f"Cảnh {scene.get('index')}: Gemini ✓")
                        else:
                            self.progress.emit(f"Cảnh {scene.get('index')}: Không tạo được ảnh")
                    except Exception as e:
                        self.progress.emit(f"Gemini failed for scene {scene.get('index')}: {e}")
                
                if img_data:
                    self.scene_image_ready.emit(scene.get('index'), img_data)
            
            # Generate social media thumbnails
            social_media = self.outline.get("social_media", {})
            versions = social_media.get("versions", [])
            
            for i, version in enumerate(versions):
                if self.should_stop:
                    break
                    
                self.progress.emit(f"Tạo thumbnail phiên bản {i+1}...")
                
                prompt = version.get("thumbnail_prompt", "")
                text_overlay = version.get("thumbnail_text_overlay", "")
                
                # Generate base thumbnail image
                try:
                    # Rate limit: 2.5s delay
                    delay = 2.5 if (len(scenes) + i) > 0 else 0
                    thumb_data = image_gen_service.generate_image_with_rate_limit(
                        prompt, 
                        delay,
                        log_callback=lambda msg: self.progress.emit(msg)
                    )
                    
                    if thumb_data:
                        # Save temp image for text overlay
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            tmp.write(thumb_data)
                            tmp_path = tmp.name
                        
                        # Add text overlay
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_out:
                            out_path = tmp_out.name
                        
                        sscript.generate_thumbnail_with_text(tmp_path, text_overlay, out_path)
                        
                        # Read final image
                        with open(out_path, 'rb') as f:
                            final_thumb = f.read()
                        
                        # Clean up temp files
                        os.unlink(tmp_path)
                        os.unlink(out_path)
                        
                        self.thumbnail_ready.emit(i, final_thumb)
                        self.progress.emit(f"Thumbnail {i+1}: ✓")
                    else:
                        self.progress.emit(f"Thumbnail {i+1}: Không tạo được")
                        
                except Exception as e:
                    self.progress.emit(f"Thumbnail {i+1} lỗi: {e}")
                
            self.finished.emit(True)
            
        except Exception as e:
            self.progress.emit(f"Lỗi: {e}")
            self.finished.emit(False)
    
    def stop(self):
        """Stop the worker"""
        self.should_stop = True
