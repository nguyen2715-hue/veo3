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
    
    def __init__(self, cfg: dict, parent=None):
        """
        Initialize script worker
        
        Args:
            cfg: Configuration dictionary with all settings
            parent: Parent QObject
        """
        super().__init__(parent)
        self.cfg = cfg
    
    def run(self):
        """Execute script generation in background thread"""
        try:
            self.progress.emit("Đang tạo kịch bản...")
            
            from services.sales_script_service import build_outline
            
            result = build_outline(self.cfg)
            
            self.progress.emit("Hoàn thành!")
            self.done.emit(result)
            
        except Exception as e:
            # Include exception type name for better error classification
            error_type = type(e).__name__
            self.error.emit(f"{error_type}: {str(e)}")
