# -*- coding: utf-8 -*-
"""
Script Worker - Non-blocking script generation using QThread
"""
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Any


class ScriptWorker(QThread):
    """Worker thread for generating scripts without blocking the UI"""
    
    # Signals
    progress = pyqtSignal(str)  # Log message
    finished = pyqtSignal(dict)  # Outline dictionary
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, cfg: Dict[str, Any], parent=None):
        """
        Initialize script worker
        
        Args:
            cfg: Configuration dictionary with project settings
            parent: Parent QObject
        """
        super().__init__(parent)
        self.cfg = cfg
        self.should_stop = False
    
    def run(self):
        """Run script generation in background thread"""
        try:
            self.progress.emit("Bắt đầu tạo kịch bản...")
            
            # Import here to avoid circular dependencies
            from services import sales_script_service as sscript
            
            # Generate outline
            outline = sscript.build_outline(self.cfg)
            
            if self.should_stop:
                self.progress.emit("Đã hủy")
                return
            
            self.progress.emit("✓ Hoàn tất tạo kịch bản")
            self.finished.emit(outline)
            
        except Exception as e:
            self.progress.emit(f"❌ Lỗi: {e}")
            self.error.emit(str(e))
    
    def stop(self):
        """Stop the worker"""
        self.should_stop = True
