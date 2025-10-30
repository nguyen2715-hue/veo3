# -*- coding: utf-8 -*-
"""
Image Worker - Non-blocking image generation using QThread
"""
from PyQt5.QtCore import QThread, pyqtSignal
import time


class ImageWorker(QThread):
    """
    Background worker for image generation
    Prevents UI freezing during image generation API calls
    """
    
    # Signals
    progress = pyqtSignal(int, str)     # Scene index, progress message
    scene_done = pyqtSignal(int, bytes) # Scene index, image bytes
    all_done = pyqtSignal()             # All scenes completed
    error = pyqtSignal(int, str)        # Scene index, error message
    
    def __init__(self, scenes: list, model: str = "gemini", parent=None):
        """
        Initialize image worker
        
        Args:
            scenes: List of scene dictionaries with 'prompt' and 'index' keys
            model: Model to use ("gemini" or "whisk")
            parent: Parent QObject
        """
        super().__init__(parent)
        self.scenes = scenes
        self.model = model
    
    def run(self):
        """Execute image generation in background thread"""
        for i, scene in enumerate(self.scenes):
            try:
                scene_idx = scene.get('index', i)
                prompt = scene.get('prompt', '')
                
                self.progress.emit(scene_idx, f"Đang tạo ảnh cảnh {scene_idx + 1}...")
                
                # Generate image based on model
                if self.model == "gemini":
                    from services.image_gen_service import generate_image_gemini
                    img_bytes = generate_image_gemini(
                        prompt,
                        log_callback=lambda msg: self.progress.emit(scene_idx, msg)
                    )
                else:
                    from services.whisk_service import generate_image
                    img_bytes = generate_image(prompt)
                
                if img_bytes:
                    self.scene_done.emit(scene_idx, img_bytes)
                else:
                    self.error.emit(scene_idx, "Không nhận được dữ liệu ảnh")
                
                # Rate limiting between requests
                time.sleep(1)
                
            except Exception as e:
                self.error.emit(scene_idx, f"Lỗi: {str(e)}")
        
        self.all_done.emit()
