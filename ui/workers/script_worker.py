# -*- coding: utf-8 -*-
"""
Script Worker - Non-blocking script generation using QThread
"""
from PyQt5.QtCore import QThread, pyqtSignal


class ScriptWorker(QThread):
    """
    Background worker for script generation
    Prevents UI freezing during LLM API calls
    """
    
    # Signals
    progress = pyqtSignal(str)  # Progress messages
    done = pyqtSignal(dict)     # Result data
    error = pyqtSignal(str)     # Error messages
    
    def __init__(self, product: str, duration: int, parent=None):
        """
        Initialize script worker
        
        Args:
            product: Product name/description
            duration: Video duration in seconds
            parent: Parent QObject
        """
        super().__init__(parent)
        self.product = product
        self.duration = duration
    
    def run(self):
        """Execute script generation in background thread"""
        try:
            self.progress.emit("Đang tạo kịch bản...")
            
            from services.sales_script_service import build_outline
            
            result = build_outline({
                'product_main': self.product,
                'duration_sec': self.duration
            })
            
            self.progress.emit("Hoàn thành!")
            self.done.emit(result)
            
        except Exception as e:
            self.error.emit(f"Lỗi tạo kịch bản: {str(e)}")
