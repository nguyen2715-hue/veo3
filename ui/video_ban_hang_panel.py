# -*- coding: utf-8 -*-
"""
Video Bán Hàng Panel - Redesigned with 3-step workflow
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
    QLineEdit, QPlainTextEdit, QPushButton, QFileDialog, QComboBox, 
    QSpinBox, QScrollArea, QToolButton, QMessageBox, QFrame, QSizePolicy,
    QTabWidget, QTextEdit
)
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import os
import math
import datetime
import time
from pathlib import Path

from services import sales_video_service as svc
from services import sales_script_service as sscript
from services import image_gen_service
from services.gemini_client import MissingAPIKey

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


class ImageGenerationWorker(QThread):
    """Worker thread for generating images (scenes + thumbnails)"""
    progress = pyqtSignal(str)  # Log message
    scene_image_ready = pyqtSignal(int, bytes)  # scene_index, image_data
    thumbnail_ready = pyqtSignal(int, bytes)  # version_index, image_data
    finished = pyqtSignal(bool)  # success
    
    def __init__(self, outline, cfg, model_paths, prod_paths, use_whisk=False):
        super().__init__()
        self.outline = outline
        self.cfg = cfg
        self.model_paths = model_paths
        self.prod_paths = prod_paths
        self.use_whisk = use_whisk
        self.should_stop = False
    
    def run(self):
        try:
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
                        
                        img_data = image_gen_service.generate_image_with_rate_limit(prompt, delay)
                        
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
                    thumb_data = image_gen_service.generate_image_with_rate_limit(prompt, delay)
                    
                    if thumb_data:
                        # Save temp image for text overlay
                        import tempfile
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
        self.should_stop = True


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
        
        # Social Media Content (3 tabs)
        self.social_tabs = QTabWidget()
        self.social_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['right_border']};
                background: {COLORS['right_card']};
            }}
            QTabBar::tab {{
                background: {COLORS['right_card']};
                color: {COLORS['right_text']};
                padding: 8px 16px;
                border: 1px solid {COLORS['right_border']};
            }}
            QTabBar::tab:selected {{
                background: {COLORS['right_accent']};
                color: white;
            }}
        """)
        
        # Create 3 social version tabs (will be populated dynamically)
        self.social_version_widgets = []
        for i in range(3):
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            
            # Caption
            lbl_caption = QLabel("Caption:")
            lbl_caption.setStyleSheet(f"color: {COLORS['right_text']}; font-weight: bold;")
            tab_layout.addWidget(lbl_caption)
            
            ed_caption = QTextEdit()
            ed_caption.setMaximumHeight(100)
            ed_caption.setStyleSheet(f"background: {COLORS['right_bg']}; color: {COLORS['right_text']};")
            ed_caption.setReadOnly(True)
            tab_layout.addWidget(ed_caption)
            
            # Copy button
            btn_copy = QPushButton("📋 Copy")
            btn_copy.clicked.connect(lambda _, e=ed_caption: self._copy_to_clipboard(e.toPlainText()))
            tab_layout.addWidget(btn_copy)
            
            # Hashtags
            lbl_hashtags = QLabel("Hashtags:")
            lbl_hashtags.setStyleSheet(f"color: {COLORS['right_text']}; font-weight: bold;")
            tab_layout.addWidget(lbl_hashtags)
            
            ed_hashtags = QTextEdit()
            ed_hashtags.setMaximumHeight(60)
            ed_hashtags.setStyleSheet(f"background: {COLORS['right_bg']}; color: {COLORS['right_text']};")
            ed_hashtags.setReadOnly(True)
            tab_layout.addWidget(ed_hashtags)
            
            # Thumbnail preview
            lbl_thumb = QLabel("Thumbnail:")
            lbl_thumb.setStyleSheet(f"color: {COLORS['right_text']}; font-weight: bold;")
            tab_layout.addWidget(lbl_thumb)
            
            img_thumb = QLabel()
            img_thumb.setFixedSize(180, 320)  # 9:16 ratio
            img_thumb.setStyleSheet(f"border: 1px solid {COLORS['right_border']}; background: black;")
            img_thumb.setAlignment(Qt.AlignCenter)
            img_thumb.setText("Chưa tạo")
            tab_layout.addWidget(img_thumb)
            
            tab_layout.addStretch(1)
            
            self.social_version_widgets.append({
                'widget': tab_widget,
                'caption': ed_caption,
                'hashtags': ed_hashtags,
                'thumbnail': img_thumb
            })
            
            self.social_tabs.addTab(tab_widget, f"Phiên bản {i+1}")
        
        layout.addWidget(self.social_tabs, 2)
        
        # Scene results
        gb_scenes = QGroupBox("Kết quả cảnh")
        gb_scenes.setStyleSheet(f"""
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
        
        sv = QVBoxLayout(gb_scenes)
        self.scenes_area = QScrollArea()
        self.scenes_area.setWidgetResizable(True)
        self.scenes_area.setMaximumHeight(300)
        
        self.scenes_root = QWidget()
        self.scenes_layout = QVBoxLayout(self.scenes_root)
        self.scenes_layout.setContentsMargins(5, 5, 5, 5)
        self.scenes_layout.setSpacing(8)
        
        self.scenes_area.setWidget(self.scenes_root)
        sv.addWidget(self.scenes_area)
        
        layout.addWidget(gb_scenes, 1)
        
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
        """Step 1: Write script and generate social media content"""
        cfg = self._collect_cfg()
        
        self._append_log("Bắt đầu tạo kịch bản...")
        self.btn_script.setEnabled(False)
        
        try:
            # Generate outline with social media content
            outline = sscript.build_outline(cfg)
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
            
        except MissingAPIKey:
            QMessageBox.warning(self, "Thiếu API Key", 
                              "Chưa nhập Google API Key trong tab Cài đặt.")
            self._append_log("❌ Thiếu Google API Key")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            self._append_log(f"❌ Lỗi: {e}")
        finally:
            self.btn_script.setEnabled(True)
    
    def _display_scene_cards(self, scenes):
        """Display scene cards in the results area"""
        # Clear existing
        while self.scenes_layout.count():
            item = self.scenes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create cards
        for scene in scenes:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['right_card']};
                    border: 1px solid {COLORS['right_border']};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
            
            card_layout = QHBoxLayout(card)
            
            # Preview image placeholder
            img_label = QLabel()
            img_label.setFixedSize(120, 120)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet(f"border: 1px dashed {COLORS['right_border']}; background: black;")
            img_label.setText("Chưa tạo")
            card_layout.addWidget(img_label)
            
            # Text info
            info_layout = QVBoxLayout()
            
            title = QLabel(f"Cảnh {scene.get('index')}")
            title.setStyleSheet(f"color: {COLORS['right_accent']}; font-weight: bold; font-size: 14px;")
            info_layout.addWidget(title)
            
            desc = QLabel(scene.get('desc', '')[:100] + "...")
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {COLORS['right_text']};")
            info_layout.addWidget(desc)
            
            info_layout.addStretch(1)
            card_layout.addLayout(info_layout, 1)
            
            self.scenes_layout.addWidget(card)
            
            # Store reference
            scene_idx = scene.get('index')
            if scene_idx:
                self.scene_images[scene_idx] = {'label': img_label, 'path': None}
        
        self.scenes_layout.addStretch(1)
    
    def _on_generate_images(self):
        """Step 2: Generate images for scenes and thumbnails"""
        if not self.last_outline:
            QMessageBox.warning(self, "Chưa có kịch bản", 
                              "Vui lòng viết kịch bản trước.")
            return
        
        cfg = self._collect_cfg()
        use_whisk = (cfg.get("image_model") == "Whisk")
        
        self._append_log("Bắt đầu tạo ảnh...")
        self.btn_images.setEnabled(False)
        
        # Create worker thread
        self.img_worker = ImageGenerationWorker(
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
            label = self.scene_images[scene_idx]['label']
            pixmap = QPixmap(str(img_path))
            label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setStyleSheet(f"border: 1px solid {COLORS['right_border']}; background: black;")
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
        
        # Update UI
        if version_idx < len(self.social_version_widgets):
            widget_data = self.social_version_widgets[version_idx]
            pixmap = QPixmap(str(img_path))
            widget_data['thumbnail'].setPixmap(
                pixmap.scaled(180, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            widget_data['thumbnail'].setStyleSheet(f"border: 1px solid {COLORS['right_border']};")
        
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
