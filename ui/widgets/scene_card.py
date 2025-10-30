# -*- coding: utf-8 -*-
"""Scene card widget with horizontal layout"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont

class SceneCard(QFrame):
    """Scene card with horizontal layout: image left, content right"""
    
    def __init__(self, scene_index, scene_data, parent=None):
        super().__init__(parent)
        self.scene_index = scene_index
        self.scene_data = scene_data
        
        # Light theme card styling
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin: 8px 0px;
            }
        """)
        
        self._build_ui()
    
    def _build_ui(self):
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Left: Image preview (portrait 3:4 ratio)
        self.img_preview = QLabel()
        self.img_preview.setFixedSize(270, 360)
        self.img_preview.setStyleSheet("""
            QLabel {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setText("Chưa tạo")
        main_layout.addWidget(self.img_preview)
        
        # Right: Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        
        # Title (blue, bold)
        lbl_title = QLabel(f"Cảnh {self.scene_index + 1}")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #1976D2;")
        content_layout.addWidget(lbl_title)
        
        # Description
        desc_text = self.scene_data.get('description', '') or self.scene_data.get('desc', '')
        lbl_desc = QLabel(desc_text)
        lbl_desc.setWordWrap(True)
        lbl_desc.setFont(QFont("Segoe UI", 11))
        lbl_desc.setStyleSheet("color: #424242; line-height: 1.5;")
        content_layout.addWidget(lbl_desc)
        
        # Collapsible prompt section
        self.btn_toggle_prompt = QPushButton("▼ Hiển thị Prompt")
        self.btn_toggle_prompt.setFlat(True)
        self.btn_toggle_prompt.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 4px 8px;
                color: #616161;
                font-size: 11px;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                color: #1976D2;
            }
        """)
        self.btn_toggle_prompt.clicked.connect(self._toggle_prompt)
        content_layout.addWidget(self.btn_toggle_prompt)
        
        self.txt_prompt = QTextEdit()
        prompt_text = self.scene_data.get('voice_over', '') or self.scene_data.get('speech', '') or self.scene_data.get('prompt_image', '')
        self.txt_prompt.setPlainText(prompt_text)
        self.txt_prompt.setReadOnly(True)
        self.txt_prompt.setMaximumHeight(80)
        self.txt_prompt.setStyleSheet("""
            QTextEdit {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-size: 10px;
                color: #616161;
            }
        """)
        self.txt_prompt.setVisible(False)
        content_layout.addWidget(self.txt_prompt)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        btn_style = """
            QPushButton {
                background: transparent;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 6px 12px;
                color: #616161;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #F5F5F5;
                border-color: #1976D2;
                color: #1976D2;
            }
        """
        
        btn_regen_script = QPushButton("📝 Tạo lại Kịch bản & Ảnh")
        btn_regen_script.setStyleSheet(btn_style)
        buttons_layout.addWidget(btn_regen_script)
        
        btn_regen_image = QPushButton("🖼️ Tạo lại Ảnh")
        btn_regen_image.setStyleSheet(btn_style)
        buttons_layout.addWidget(btn_regen_image)
        
        btn_create_video = QPushButton("🎬 Tạo Video")
        btn_create_video.setStyleSheet(btn_style)
        buttons_layout.addWidget(btn_create_video)
        
        btn_play_audio = QPushButton("🔊 Phát âm thanh")
        btn_play_audio.setStyleSheet(btn_style)
        buttons_layout.addWidget(btn_play_audio)
        
        btn_download = QPushButton("⬇️ Tải ảnh")
        btn_download.setStyleSheet(btn_style)
        buttons_layout.addWidget(btn_download)
        
        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)
        content_layout.addStretch()
        
        main_layout.addLayout(content_layout, 1)
    
    def _toggle_prompt(self):
        is_visible = self.txt_prompt.isVisible()
        self.txt_prompt.setVisible(not is_visible)
        self.btn_toggle_prompt.setText("▲ Ẩn Prompt" if not is_visible else "▼ Hiển thị Prompt")
    
    def set_image(self, image_bytes):
        """Set image from bytes"""
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        self.img_preview.setPixmap(pixmap.scaled(270, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def set_image_pixmap(self, pixmap):
        """Set image from pixmap"""
        self.img_preview.setPixmap(pixmap.scaled(270, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
