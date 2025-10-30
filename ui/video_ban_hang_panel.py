# -*- coding: utf-8 -*-
"""
Video Bán Hàng Panel - Redesigned with 3-step workflow
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
    QLineEdit, QPlainTextEdit, QPushButton, QFileDialog, QComboBox, 
    QSpinBox, QScrollArea, QToolButton, QMessageBox, QFrame, QSizePolicy,
    QTabWidget, QTextEdit, QDialog, QApplication
)
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import os
import math
import datetime
import time
from pathlib import Path

from services import sales_video_service as svc
from services.gemini_client import MissingAPIKey
from ui.widgets.scene_card import SceneCard
from ui.styles.light_theme import COLORS as LIGHT_COLORS
# Workers that handle script and image generation in background threads
# They internally import and use sales_script_service and image_gen_service
from ui.workers.script_worker import ScriptWorker
from ui.workers.image_worker import ImageWorker

# Fonts
FONT_LABEL = QFont()
FONT_LABEL.setPixelSize(13)
FONT_INPUT = QFont()
FONT_INPUT.setPixelSize(12)

# Sizes
THUMBNAIL_SIZE = 60
MODEL_IMG = 128

# Color scheme
COLORS = {
    'left_bg': '#e8f4f8',
    'left_group': '#f0f8fc',
    'left_border': '#c5e1eb',
    'left_button': '#0891b2',
    'right_bg': '#1a202c',
    'right_card': '#2d3748',
    'right_border': '#4a5568',
    'right_text': '#e2e8f0',
    'right_accent': '#60a5fa',
}


class SceneCardWidget(QFrame):
    """Scene card widget with image preview and action buttons"""
    
    def __init__(self, scene_data, parent=None):
        super().__init__(parent)
        self.scene_data = scene_data
        self.image_label = None
        self._build_ui()
    
    def _build_ui(self):
        """Build the scene card UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['right_card']};
                border: 1px solid {COLORS['right_border']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        
        # Preview image
        self.image_label = QLabel()
        self.image_label.setFixedSize(320, 180)  # 16:9 preview
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"border: 1px dashed {COLORS['right_border']}; background: black;")
        self.image_label.setText("Chưa tạo")
        layout.addWidget(self.image_label)
        
        # Info and buttons section
        info_layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"Cảnh {self.scene_data.get('index')}")
        title.setStyleSheet(f"color: {COLORS['right_accent']}; font-weight: bold; font-size: 16px;")
        info_layout.addWidget(title)
        
        # Description
        desc_text = self.scene_data.get('desc', '')
        if len(desc_text) > 150:
            desc_text = desc_text[:150] + "..."
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['right_text']}; font-size: 12px;")
        info_layout.addWidget(desc)
        
        # Speech text
        speech_text = self.scene_data.get('speech', '')
        if len(speech_text) > 100:
            speech_text = speech_text[:100] + "..."
        speech = QLabel(f"🎤 {speech_text}")
        speech.setWordWrap(True)
        speech.setStyleSheet(f"color: #aaa; font-size: 11px; font-style: italic;")
        info_layout.addWidget(speech)
        
        info_layout.addStretch(1)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        # Prompt button
        btn_prompt = QPushButton("📝 Prompt ảnh/video")
        btn_prompt.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #60a5fa;
            }
        """)
        btn_prompt.clicked.connect(self._show_prompts)
        btn_layout.addWidget(btn_prompt)
        
        # Regenerate button
        btn_regen = QPushButton("🔄 Tạo lại")
        btn_regen.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #26A69A;
            }
        """)
        btn_layout.addWidget(btn_regen)
        
        # Video button
        btn_video = QPushButton("🎬 Video")
        btn_video.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #0E7C66;
            }
        """)
        btn_layout.addWidget(btn_video)
        
        info_layout.addLayout(btn_layout)
        
        layout.addLayout(info_layout, 1)
    
    def _show_prompts(self):
        """Show prompt dialog with image and video prompts"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Prompts - Cảnh {self.scene_data.get('index')}")
        dialog.setFixedSize(700, 500)
        dialog.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['right_bg']};
            }}
            QLabel {{
                color: {COLORS['right_text']};
                font-weight: bold;
                font-size: 13px;
            }}
            QTextEdit {{
                background: {COLORS['right_card']};
                color: {COLORS['right_text']};
                border: 1px solid {COLORS['right_border']};
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 11px;
            }}
            QPushButton {{
                background: {COLORS['right_accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #4A90E2;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Image prompt section
        lbl_img = QLabel("📷 Prompt Ảnh:")
        layout.addWidget(lbl_img)
        
        ed_img_prompt = QTextEdit()
        ed_img_prompt.setReadOnly(True)
        ed_img_prompt.setPlainText(self.scene_data.get('prompt_image', ''))
        ed_img_prompt.setMaximumHeight(180)
        layout.addWidget(ed_img_prompt)
        
        btn_copy_img = QPushButton("📋 Copy Prompt Ảnh")
        btn_copy_img.clicked.connect(lambda: self._copy_to_clipboard(self.scene_data.get('prompt_image', '')))
        layout.addWidget(btn_copy_img)
        
        # Video prompt section
        lbl_vid = QLabel("🎬 Prompt Video:")
        layout.addWidget(lbl_vid)
        
        ed_vid_prompt = QTextEdit()
        ed_vid_prompt.setReadOnly(True)
        ed_vid_prompt.setPlainText(self.scene_data.get('prompt_video', ''))
        ed_vid_prompt.setMaximumHeight(180)
        layout.addWidget(ed_vid_prompt)
        
        btn_copy_vid = QPushButton("📋 Copy Prompt Video")
        btn_copy_vid.clicked.connect(lambda: self._copy_to_clipboard(self.scene_data.get('prompt_video', '')))
        layout.addWidget(btn_copy_vid)
        
        # Close button
        btn_close = QPushButton("✖ Đóng")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.exec_()
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show brief feedback
        QMessageBox.information(self, "Thành công", "Đã copy vào clipboard!")
    
    def set_image(self, pixmap):
        """Set the preview image"""
        if self.image_label:
            self.image_label.setPixmap(pixmap.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_label.setStyleSheet(f"border: 1px solid {COLORS['right_border']}; background: black;")


# ImageGenerationWorker moved to ui/workers/image_worker.py


class VideoBanHangPanel(QWidget):
    """Redesigned Video Bán Hàng panel with 3-step workflow"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_rows = []
        self.prod_paths = []
        self.last_outline = None
        self.scene_images = {}  # scene_index -> image_path
        self.thumbnail_images = {}  # version_index -> image_path
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the 2-column UI"""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # Main horizontal layout: Left + Right columns
        main = QHBoxLayout()
        main.setSpacing(0)
        main.setContentsMargins(0, 0, 0, 0)
        
        # Left column (380px fixed, light blue)
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(380)
        self.left_widget.setStyleSheet(f"background-color: {COLORS['left_bg']};")
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        self._build_left_column(left_layout)
        
        # Right column (flexible, dark)
        self.right_widget = QWidget()
        self.right_widget.setStyleSheet(f"background-color: {COLORS['right_bg']};")
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        self._build_right_column(right_layout)
        
        main.addWidget(self.left_widget)
        main.addWidget(self.right_widget, 1)
        
        root.addLayout(main)
    
    def _build_left_column(self, layout):
        """Build left column with project settings"""
        
        # Project info
        gb_proj = self._create_group("Dự án")
        g = QGridLayout(gb_proj)
        g.setVerticalSpacing(6)
        
        self.ed_name = QLineEdit()
        self.ed_name.setFont(FONT_INPUT)
        self.ed_name.setPlaceholderText("Tự tạo nếu để trống")
        self.ed_name.setText(svc.default_project_name())
        
        self.ed_idea = QPlainTextEdit()
        self.ed_idea.setFont(FONT_INPUT)
        self.ed_idea.setMinimumHeight(60)
        self.ed_idea.setPlaceholderText("Ý tưởng (2–3 dòng)")
        
        self.ed_product = QPlainTextEdit()
        self.ed_product.setFont(FONT_INPUT)
        self.ed_product.setMinimumHeight(100)
        self.ed_product.setPlaceholderText("Nội dung chính / Đặc điểm sản phẩm")
        
        g.addWidget(QLabel("Tên dự án:"), 0, 0)
        g.addWidget(self.ed_name, 1, 0)
        g.addWidget(QLabel("Ý tưởng:"), 2, 0)
        g.addWidget(self.ed_idea, 3, 0)
        g.addWidget(QLabel("Nội dung:"), 4, 0)
        g.addWidget(self.ed_product, 5, 0)
        
        for w in gb_proj.findChildren(QLabel):
            w.setFont(FONT_LABEL)
        
        layout.addWidget(gb_proj)
        
        # Model info with thumbnails
        gb_models = self._create_group("Thông tin người mẫu")
        mv = QVBoxLayout(gb_models)
        
        # Description
        lbl = QLabel("Mô tả người mẫu:")
        lbl.setFont(FONT_LABEL)
        mv.addWidget(lbl)
        
        self.ed_model_desc = QPlainTextEdit()
        self.ed_model_desc.setFont(FONT_INPUT)
        self.ed_model_desc.setMaximumHeight(80)
        self.ed_model_desc.setPlaceholderText("Mô tả chi tiết (JSON hoặc text)")
        mv.addWidget(self.ed_model_desc)
        
        # Image selection
        btn_model = QPushButton("📁 Chọn ảnh người mẫu")
        btn_model.clicked.connect(self._pick_model_images)
        mv.addWidget(btn_model)
        
        # Thumbnail container
        self.model_thumb_container = QHBoxLayout()
        self.model_thumb_container.setSpacing(4)
        mv.addLayout(self.model_thumb_container)
        
        layout.addWidget(gb_models)
        
        # Product images with thumbnails
        gb_prod = self._create_group("Ảnh sản phẩm")
        pv = QVBoxLayout(gb_prod)
        
        btn_prod = QPushButton("📁 Chọn ảnh sản phẩm")
        btn_prod.clicked.connect(self._pick_product_images)
        pv.addWidget(btn_prod)
        
        # Thumbnail container
        self.prod_thumb_container = QHBoxLayout()
        self.prod_thumb_container.setSpacing(4)
        pv.addLayout(self.prod_thumb_container)
        
        layout.addWidget(gb_prod)
        
        # Video settings (Grid 2x5)
        gb_cfg = self._create_group("Cài đặt video")
        s = QGridLayout(gb_cfg)
        s.setVerticalSpacing(8)
        s.setHorizontalSpacing(10)
        
        def make_widget(widget_class, **kwargs):
            w = widget_class()
            w.setMinimumHeight(32)
            for k, v in kwargs.items():
                if hasattr(w, k):
                    getattr(w, k)(v) if callable(getattr(w, k)) else setattr(w, k, v)
            return w
        
        self.cb_style = make_widget(QComboBox)
        self.cb_style.addItems(["Viral", "KOC Review", "Kể chuyện"])
        
        self.cb_imgstyle = make_widget(QComboBox)
        self.cb_imgstyle.addItems(["Điện ảnh", "Hiện đại/Trendy", "Anime", "Hoạt hình 3D"])
        
        self.cb_script_model = make_widget(QComboBox)
        self.cb_script_model.addItems(["Gemini 2.5 Flash (mặc định)", "ChatGPT5 (tuỳ chọn)"])
        
        self.cb_image_model = make_widget(QComboBox)
        self.cb_image_model.addItems(["Gemini", "Whisk"])
        
        self.ed_voice = make_widget(QLineEdit)
        self.ed_voice.setPlaceholderText("ElevenLabs VoiceID")
        
        self.cb_lang = make_widget(QComboBox)
        self.cb_lang.addItems(["vi", "en"])
        
        self.sp_duration = make_widget(QSpinBox)
        self.sp_duration.setRange(8, 1200)
        self.sp_duration.setSingleStep(8)
        self.sp_duration.setValue(32)
        self.sp_duration.valueChanged.connect(self._update_scenes)
        
        self.sp_videos = make_widget(QSpinBox)
        self.sp_videos.setRange(1, 4)
        self.sp_videos.setValue(1)
        
        self.cb_ratio = make_widget(QComboBox)
        self.cb_ratio.addItems(["9:16", "16:9", "1:1", "4:5"])
        
        self.cb_social = make_widget(QComboBox)
        self.cb_social.addItems(['TikTok', 'Facebook', 'YouTube'])
        
        self.lb_scenes = QLabel("Số cảnh: 4")
        self.lb_scenes.setFont(FONT_LABEL)
        
        # Grid layout: 2 columns x 5 rows
        row = 0
        s.addWidget(QLabel("Phong cách KB:"), row, 0)
        s.addWidget(self.cb_style, row, 1)
        s.addWidget(QLabel("Phong cách HA:"), row, 2)
        s.addWidget(self.cb_imgstyle, row, 3)
        
        row += 1
        s.addWidget(QLabel("Model KB:"), row, 0)
        s.addWidget(self.cb_script_model, row, 1)
        s.addWidget(QLabel("Model tạo ảnh:"), row, 2)
        s.addWidget(self.cb_image_model, row, 3)
        
        row += 1
        s.addWidget(QLabel("Lời thoại:"), row, 0)
        s.addWidget(self.ed_voice, row, 1)
        s.addWidget(QLabel("Ngôn ngữ:"), row, 2)
        s.addWidget(self.cb_lang, row, 3)
        
        row += 1
        s.addWidget(QLabel("Thời lượng (s):"), row, 0)
        s.addWidget(self.sp_duration, row, 1)
        s.addWidget(QLabel("Số video/cảnh:"), row, 2)
        s.addWidget(self.sp_videos, row, 3)
        
        row += 1
        s.addWidget(QLabel("Tỉ lệ:"), row, 0)
        s.addWidget(self.cb_ratio, row, 1)
        s.addWidget(QLabel("Nền tảng:"), row, 2)
        s.addWidget(self.cb_social, row, 3)
        
        row += 1
        s.addWidget(self.lb_scenes, row, 0, 1, 4)
        
        for w in gb_cfg.findChildren(QLabel):
            w.setFont(FONT_LABEL)
        
        layout.addWidget(gb_cfg)
        layout.addStretch(1)
        
        self._update_scenes()
    
    def _build_right_column(self, layout):
        """Build right column with results and logs"""
        
        # Tab widget for results
        self.results_tabs = QTabWidget()
        self.results_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {LIGHT_COLORS['background']};
                border: 1px solid {LIGHT_COLORS['border']};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {LIGHT_COLORS['hover']};
                color: #757575;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background: {LIGHT_COLORS['background']};
                color: {LIGHT_COLORS['primary']};
                border-bottom: 3px solid {LIGHT_COLORS['primary']};
            }}
            QTabBar::tab:hover {{
                background: #EEEEEE;
            }}
        """)
        
        # Tab 1: Scenes (card list)
        scenes_tab = self._build_scenes_tab()
        self.results_tabs.addTab(scenes_tab, "🎬 Cảnh")
        
        # Tab 2: Thumbnail
        thumbnail_tab = self._build_thumbnail_tab()
        self.results_tabs.addTab(thumbnail_tab, "📺 Thumbnail")
        
        # Tab 3: Social
        social_tab = self._build_social_tab()
        self.results_tabs.addTab(social_tab, "📱 Social")
        
        layout.addWidget(self.results_tabs, 3)
        
        # Log area
        gb_log = QGroupBox("Nhật ký xử lý")
        gb_log.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {COLORS['right_text']};
                border: 1px solid {COLORS['right_border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                background: {COLORS['right_card']};
            }}
        """)
        
        lv = QVBoxLayout(gb_log)
        self.ed_log = QPlainTextEdit()
        self.ed_log.setFont(FONT_INPUT)
        self.ed_log.setReadOnly(True)
        self.ed_log.setMaximumHeight(150)
        self.ed_log.setStyleSheet(f"background: {COLORS['right_bg']}; color: {COLORS['right_text']};")
        lv.addWidget(self.ed_log)
        
        layout.addWidget(gb_log, 1)
        
        # 3 buttons at bottom
        btn_layout = QHBoxLayout()
        
        self.btn_script = QPushButton("📝 Viết kịch bản")
        self.btn_script.setMinimumHeight(40)
        self.btn_script.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #1565C0;
            }
            QPushButton:disabled {
                background: #666;
            }
        """)
        self.btn_script.clicked.connect(self._on_write_script)
        
        self.btn_images = QPushButton("🎨 Tạo ảnh")
        self.btn_images.setMinimumHeight(40)
        self.btn_images.setStyleSheet("""
            QPushButton {
                background: #26A69A;
                color: white;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #1E8E7E;
            }
            QPushButton:disabled {
                background: #666;
            }
        """)
        self.btn_images.clicked.connect(self._on_generate_images)
        self.btn_images.setEnabled(False)
        
        self.btn_video = QPushButton("🎬 Tạo video")
        self.btn_video.setMinimumHeight(40)
        self.btn_video.setStyleSheet("""
            QPushButton {
                background: #0E7C66;
                color: white;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #0C6B58;
            }
            QPushButton:disabled {
                background: #666;
            }
        """)
        self.btn_video.clicked.connect(self._on_generate_video)
        self.btn_video.setEnabled(False)
        
        btn_layout.addWidget(self.btn_script)
        btn_layout.addWidget(self.btn_images)
        btn_layout.addWidget(self.btn_video)
        
        layout.addLayout(btn_layout)
    
    def _build_scenes_tab(self):
        """Build scenes tab with vertical card list"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {LIGHT_COLORS['background']}; }}")
        
        container = QWidget()
        self.scenes_layout = QVBoxLayout(container)
        self.scenes_layout.setContentsMargins(16, 16, 16, 16)
        self.scenes_layout.setSpacing(0)
        
        # Scene cards will be added dynamically
        self.scene_cards = []
        
        self.scenes_layout.addStretch()
        scroll.setWidget(container)
        return scroll
    
    def _build_thumbnail_tab(self):
        """Build thumbnail tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {LIGHT_COLORS['background']}; }}")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Create 3 thumbnail version widgets
        self.thumbnail_widgets = []
        for i in range(3):
            # Version card
            version_card = QFrame()
            version_card.setStyleSheet(f"""
                QFrame {{
                    background: {LIGHT_COLORS['card']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 8px;
                    padding: 16px;
                }}
            """)
            
            card_layout = QVBoxLayout(version_card)
            
            # Title
            lbl_title = QLabel(f"Phiên bản {i+1}")
            lbl_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
            lbl_title.setStyleSheet(f"color: {LIGHT_COLORS['primary']};")
            card_layout.addWidget(lbl_title)
            
            # Thumbnail image
            img_thumb = QLabel()
            img_thumb.setFixedSize(270, 480)  # 9:16 ratio
            img_thumb.setStyleSheet(f"""
                QLabel {{
                    background: {LIGHT_COLORS['hover']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 4px;
                }}
            """)
            img_thumb.setAlignment(Qt.AlignCenter)
            img_thumb.setText("Chưa tạo")
            card_layout.addWidget(img_thumb)
            
            self.thumbnail_widgets.append({'thumbnail': img_thumb})
            layout.addWidget(version_card)
        
        layout.addStretch()
        scroll.setWidget(container)
        return scroll
    
    def _build_social_tab(self):
        """Build social media tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {LIGHT_COLORS['background']}; }}")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Create 3 social version widgets
        self.social_version_widgets = []
        for i in range(3):
            # Version card
            version_card = QFrame()
            version_card.setStyleSheet(f"""
                QFrame {{
                    background: {LIGHT_COLORS['card']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 8px;
                    padding: 16px;
                }}
            """)
            
            card_layout = QVBoxLayout(version_card)
            
            # Title
            lbl_title = QLabel(f"Phiên bản {i+1}")
            lbl_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
            lbl_title.setStyleSheet(f"color: {LIGHT_COLORS['primary']};")
            card_layout.addWidget(lbl_title)
            
            # Caption
            lbl_caption = QLabel("Caption:")
            lbl_caption.setFont(QFont("Segoe UI", 12, QFont.Bold))
            lbl_caption.setStyleSheet(f"color: {LIGHT_COLORS['text_secondary']};")
            card_layout.addWidget(lbl_caption)
            
            ed_caption = QTextEdit()
            ed_caption.setMaximumHeight(100)
            ed_caption.setStyleSheet(f"""
                QTextEdit {{
                    background: {LIGHT_COLORS['hover']};
                    color: {LIGHT_COLORS['text_primary']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            ed_caption.setReadOnly(True)
            card_layout.addWidget(ed_caption)
            
            # Copy button
            btn_copy = QPushButton("📋 Copy Caption")
            btn_copy.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {LIGHT_COLORS['divider']};
                    border-radius: 4px;
                    padding: 6px 12px;
                    color: {LIGHT_COLORS['text_secondary']};
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {LIGHT_COLORS['hover']};
                    border-color: {LIGHT_COLORS['primary']};
                    color: {LIGHT_COLORS['primary']};
                }}
            """)
            btn_copy.clicked.connect(lambda _, e=ed_caption: self._copy_to_clipboard(e.toPlainText()))
            card_layout.addWidget(btn_copy)
            
            # Hashtags
            lbl_hashtags = QLabel("Hashtags:")
            lbl_hashtags.setFont(QFont("Segoe UI", 12, QFont.Bold))
            lbl_hashtags.setStyleSheet(f"color: {LIGHT_COLORS['text_secondary']};")
            card_layout.addWidget(lbl_hashtags)
            
            ed_hashtags = QTextEdit()
            ed_hashtags.setMaximumHeight(60)
            ed_hashtags.setStyleSheet(f"""
                QTextEdit {{
                    background: {LIGHT_COLORS['hover']};
                    color: {LIGHT_COLORS['text_primary']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            ed_hashtags.setReadOnly(True)
            card_layout.addWidget(ed_hashtags)
            
            self.social_version_widgets.append({
                'widget': version_card,
                'caption': ed_caption,
                'hashtags': ed_hashtags
            })
            
            layout.addWidget(version_card)
        
        layout.addStretch()
        scroll.setWidget(container)
        return scroll
    
    def _create_group(self, title):
        """Create a styled group box"""
        gb = QGroupBox(title)
        gb.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                background: {COLORS['left_group']};
                border: 1px solid {COLORS['left_border']};
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
            }}
        """)
        return gb
    
    def _update_scenes(self):
        """Update scene count label"""
        n = max(1, math.ceil(self.sp_duration.value() / 8.0))
        self.lb_scenes.setText(f"Số cảnh: {n}")
    
    def _pick_model_images(self):
        """Pick model images and show thumbnails"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh người mẫu", "", 
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not files:
            return
        
        self.model_rows = files
        self._refresh_model_thumbnails()
    
    def _pick_product_images(self):
        """Pick product images and show thumbnails"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh sản phẩm", "", 
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not files:
            return
        
        self.prod_paths = files
        self._refresh_product_thumbnails()
    
    def _refresh_model_thumbnails(self):
        """Refresh model image thumbnails"""
        # Clear existing
        while self.model_thumb_container.count():
            item = self.model_thumb_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Show max 5 thumbnails
        max_show = 5
        for i, path in enumerate(self.model_rows[:max_show]):
            thumb = QLabel()
            thumb.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            thumb.setScaledContents(True)
            thumb.setPixmap(QPixmap(path).scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            thumb.setStyleSheet("border: 1px solid #90CAF9;")
            self.model_thumb_container.addWidget(thumb)
        
        # Show "+N" if more
        if len(self.model_rows) > max_show:
            extra = QLabel(f"+{len(self.model_rows) - max_show}")
            extra.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            extra.setAlignment(Qt.AlignCenter)
            extra.setStyleSheet("border: 1px dashed #666; font-weight: bold;")
            self.model_thumb_container.addWidget(extra)
        
        self.model_thumb_container.addStretch(1)
    
    def _refresh_product_thumbnails(self):
        """Refresh product image thumbnails"""
        # Clear existing
        while self.prod_thumb_container.count():
            item = self.prod_thumb_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Show max 5 thumbnails
        max_show = 5
        for i, path in enumerate(self.prod_paths[:max_show]):
            thumb = QLabel()
            thumb.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            thumb.setScaledContents(True)
            thumb.setPixmap(QPixmap(path).scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            thumb.setStyleSheet("border: 1px solid #90CAF9;")
            self.prod_thumb_container.addWidget(thumb)
        
        # Show "+N" if more
        if len(self.prod_paths) > max_show:
            extra = QLabel(f"+{len(self.prod_paths) - max_show}")
            extra.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            extra.setAlignment(Qt.AlignCenter)
            extra.setStyleSheet("border: 1px dashed #666; font-weight: bold;")
            self.prod_thumb_container.addWidget(extra)
        
        self.prod_thumb_container.addStretch(1)
    
    def _collect_cfg(self):
        """Collect configuration from UI"""
        return {
            "project_name": (self.ed_name.text() or '').strip() or svc.default_project_name(),
            "idea": self.ed_idea.toPlainText(),
            "product_main": self.ed_product.toPlainText(),
            "script_style": self.cb_style.currentText(),
            "image_style": self.cb_imgstyle.currentText(),
            "script_model": self.cb_script_model.currentText(),
            "image_model": self.cb_image_model.currentText(),
            "voice_id": self.ed_voice.text().strip(),
            "duration_sec": int(self.sp_duration.value()),
            "videos_count": int(self.sp_videos.value()),
            "ratio": self.cb_ratio.currentText(),
            "speech_lang": self.cb_lang.currentText(),
            "social_platform": self.cb_social.currentText(),
            "first_model_json": self.ed_model_desc.toPlainText(),
            "product_count": len(self.prod_paths),
        }
    
    def _append_log(self, msg):
        """Append message to log"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.ed_log.appendPlainText(line)
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self._append_log("Đã copy vào clipboard")
    
    def _on_write_script(self):
        """Step 1: Write script and generate social media content (non-blocking)"""
        cfg = self._collect_cfg()
        
        self._append_log("Bắt đầu tạo kịch bản...")
        self.btn_script.setEnabled(False)
        
        try:
            # Create and start script worker
            self.script_worker = ScriptWorker(cfg)
            self.script_worker.progress.connect(self._append_log)
            self.script_worker.finished.connect(self._on_script_finished)
            self.script_worker.error.connect(self._on_script_error)
            self.script_worker.start()
            
        except MissingAPIKey:
            QMessageBox.warning(self, "Thiếu API Key", 
                              "Chưa nhập Google API Key trong tab Cài đặt.")
            self._append_log("❌ Thiếu Google API Key")
            self.btn_script.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            self._append_log(f"❌ Lỗi: {e}")
            self.btn_script.setEnabled(True)
    
    def _on_script_finished(self, outline):
        """Handle script generation completion"""
        try:
            self.last_outline = outline
            
            # Display social media versions
            social_media = outline.get("social_media", {})
            versions = social_media.get("versions", [])
            
            for i, version in enumerate(versions[:3]):
                if i < len(self.social_version_widgets):
                    widget_data = self.social_version_widgets[i]
                    
                    # Set caption
                    caption = version.get("caption", "")
                    widget_data['caption'].setPlainText(caption)
                    
                    # Set hashtags
                    hashtags = " ".join(version.get("hashtags", []))
                    widget_data['hashtags'].setPlainText(hashtags)
            
            # Display scene cards
            self._display_scene_cards(outline.get("scenes", []))
            
            self._append_log(f"✓ Tạo kịch bản thành công ({len(outline.get('scenes', []))} cảnh)")
            self._append_log(f"✓ Tạo {len(versions)} phiên bản social media")
            
            # Enable next button
            self.btn_images.setEnabled(True)
            
        except Exception as e:
            self._append_log(f"❌ Lỗi hiển thị: {e}")
        finally:
            self.btn_script.setEnabled(True)
    
    def _on_script_error(self, error_msg):
        """Handle script generation error"""
        QMessageBox.critical(self, "Lỗi", error_msg)
        self.btn_script.setEnabled(True)
    
    def _display_scene_cards(self, scenes):
        """Display scene cards in the results area"""
        # Clear existing cards (but keep the stretch)
        while self.scenes_layout.count() > 1:
            item = self.scenes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Reset scene_cards list
        self.scene_cards = []
        self.scene_images = {}
        
        # Create cards using new SceneCard widget
        for i, scene in enumerate(scenes):
            # Get scene index (1-based in data)
            scene_idx = scene.get('index', i + 1)
            
            # Create new SceneCard (0-based index for display)
            card = SceneCard(i, scene)
            self.scenes_layout.insertWidget(i, card)
            
            # Store references
            self.scene_cards.append(card)
            self.scene_images[scene_idx] = {'card': card, 'label': card.img_preview, 'path': None}
    
    def _on_generate_images(self):
        """Step 2: Generate images for scenes and thumbnails (non-blocking)"""
        if not self.last_outline:
            QMessageBox.warning(self, "Chưa có kịch bản", 
                              "Vui lòng viết kịch bản trước.")
            return
        
        cfg = self._collect_cfg()
        use_whisk = (cfg.get("image_model") == "Whisk")
        
        self._append_log("Bắt đầu tạo ảnh...")
        self.btn_images.setEnabled(False)
        
        # Create worker thread
        self.img_worker = ImageWorker(
            self.last_outline, cfg, 
            self.model_rows, self.prod_paths,
            use_whisk
        )
        
        self.img_worker.progress.connect(self._append_log)
        self.img_worker.scene_image_ready.connect(self._on_scene_image_ready)
        self.img_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.img_worker.finished.connect(self._on_images_finished)
        
        self.img_worker.start()
    
    def _on_scene_image_ready(self, scene_idx, img_data):
        """Handle scene image ready"""
        # Save image to file
        cfg = self._collect_cfg()
        dirs = svc.ensure_project_dirs(cfg["project_name"])
        img_path = dirs["preview"] / f"scene_{scene_idx}.png"
        
        with open(img_path, 'wb') as f:
            f.write(img_data)
        
        # Update UI
        if scene_idx in self.scene_images:
            card = self.scene_images[scene_idx].get('card')
            if card:
                pixmap = QPixmap(str(img_path))
                card.set_image_pixmap(pixmap)
            self.scene_images[scene_idx]['path'] = str(img_path)
        
        self._append_log(f"✓ Ảnh cảnh {scene_idx} đã sẵn sàng")
    
    def _on_thumbnail_ready(self, version_idx, img_data):
        """Handle thumbnail image ready"""
        # Save and display thumbnail
        cfg = self._collect_cfg()
        dirs = svc.ensure_project_dirs(cfg["project_name"])
        img_path = dirs["preview"] / f"thumbnail_v{version_idx+1}.png"
        
        with open(img_path, 'wb') as f:
            f.write(img_data)
        
        # Update UI - thumbnail tab
        if version_idx < len(self.thumbnail_widgets):
            widget_data = self.thumbnail_widgets[version_idx]
            pixmap = QPixmap(str(img_path))
            widget_data['thumbnail'].setPixmap(
                pixmap.scaled(270, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            widget_data['thumbnail'].setStyleSheet(f"""
                QLabel {{
                    background: {LIGHT_COLORS['hover']};
                    border: 1px solid {LIGHT_COLORS['border']};
                    border-radius: 4px;
                }}
            """)
        
        self._append_log(f"✓ Thumbnail phiên bản {version_idx+1} đã sẵn sàng")
    
    def _on_images_finished(self, success):
        """Handle image generation finished"""
        if success:
            self._append_log("✓ Hoàn tất tạo ảnh")
            self.btn_video.setEnabled(True)
        else:
            self._append_log("❌ Có lỗi khi tạo ảnh")
        
        self.btn_images.setEnabled(True)
    
    def _on_generate_video(self):
        """Step 3: Generate videos using scene images"""
        if not self.last_outline:
            QMessageBox.warning(self, "Chưa có kịch bản", 
                              "Vui lòng viết kịch bản trước.")
            return
        
        if not any(img.get('path') for img in self.scene_images.values()):
            QMessageBox.warning(self, "Chưa có ảnh", 
                              "Vui lòng tạo ảnh trước.")
            return
        
        self._append_log("Bắt đầu tạo video...")
        self.btn_video.setEnabled(False)
        
        # TODO: Implement video generation workflow
        # This would call the sales_pipeline with the generated images
        
        QMessageBox.information(self, "Thông báo", 
                              "Chức năng tạo video sẽ được triển khai trong phiên bản tiếp theo.")
        
        self.btn_video.setEnabled(True)


# QSS AUTOLOAD
try:
    import os
    from PyQt5.QtWidgets import QApplication, QWidget
    
    def _qss_autoload_once(self):
        app = QApplication.instance()
        if app is None:
            return
        if getattr(app, '_vsu_qss_loaded', False):
            return
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qss_path = os.path.join(base, 'styles', 'app.qss')
            if os.path.exists(qss_path):
                with open(qss_path, 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
                app._vsu_qss_loaded = True
        except Exception as _e:
            print('QSS autoload error:', _e)
    
    if 'VideoBanHangPanel' in globals():
        def _vsu_showEvent_qss(self, e):
            try:
                _qss_autoload_once(self)
            except Exception as _e:
                print('QSS load err:', _e)
            try:
                QWidget.showEvent(self, e)
            except Exception:
                pass
        
        VideoBanHangPanel.showEvent = _vsu_showEvent_qss
except Exception as _e:
    print('init QSS autoload error:', _e)
