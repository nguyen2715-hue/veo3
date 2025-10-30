# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QGroupBox,QLabel,QLineEdit,
 QPlainTextEdit,QPushButton,QFileDialog,QComboBox,QSpinBox,QScrollArea,QToolButton,QMessageBox,QFrame,QSizePolicy)
from PyQt5.QtGui import QFont,QPixmap
from PyQt5.QtCore import Qt,QThread,pyqtSignal
import os,math,datetime
from services import sales_video_service as svc
from services import sales_script_service as sscript
from services import sales_pipeline
from services.gemini_client import MissingAPIKey

FONT_LABEL=QFont(); FONT_LABEL.setPixelSize(13)
FONT_INPUT=QFont(); FONT_INPUT.setPixelSize(12)

MODEL_IMG=128
PROD_IMG=102

def _groupbox(w):
    w.setStyleSheet('QGroupBox{font-weight:bold;font-size:13px;background:#E9F4FF;border:1px solid #9ED0FF;border-radius:8px;margin-top:6px;padding:8px;}')

class _Worker(QThread):
    progress=pyqtSignal(object,object)
    finished=pyqtSignal(list)
    startedSig=pyqtSignal(str)
    def __init__(self,cfgv,scenes,model_paths,prod_paths,out_root,parent=None):
        super().__init__(parent); self.cfgv=cfgv; self.scenes=scenes; self.model_paths=model_paths; self.prod_paths=prod_paths; self.out_root=out_root
    def run(self):
        self.startedSig.emit("start")
        result=sales_pipeline.start_pipeline(self.cfgv["project_name"], self.cfgv["ratio"], self.scenes, self.cfgv["image_style"], self.cfgv["product_main"], self.cfgv["speech_lang"], self.model_paths, self.prod_paths, copies=int(self.cfgv["videos_count"]))
        try:
            from services.labs_flow_service import LabsClient; from utils import config as cfg; client=LabsClient((cfg.load() or {}).get("tokens") or [], on_event=None)
        except Exception: client=None
        done=[]
        if client and result.get("jobs"):
            out_dir=os.path.join(self.out_root,"Video"); done=sales_pipeline.poll_and_download(client,result["jobs"],out_dir,on_progress=lambda j,info:self.progress.emit(j,info))
        self.finished.emit(done)

class VideoBanHangPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.model_rows=[]; self.prod_paths=[]; self.cards={}; self.last_outline=None
        self._build_ui()

    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(10,10,10,10); root.setSpacing(8)
        main=QHBoxLayout(); main.setSpacing(10); self.left=QVBoxLayout(); self.right=QVBoxLayout(); main.addLayout(self.left,1); main.addLayout(self.right,2); root.addLayout(main)

        gb_proj=QGroupBox("Dự án"); _groupbox(gb_proj); g=QGridLayout(gb_proj); g.setVerticalSpacing(6)
        self.ed_name=QLineEdit(); self.ed_name.setFont(FONT_INPUT); self.ed_name.setPlaceholderText("Tự tạo nếu để trống"); self.ed_name.setText(svc.default_project_name())
        self.ed_name.setObjectName('ed_name')
        self.ed_idea=QPlainTextEdit(); self.ed_idea.setFont(FONT_INPUT); self.ed_idea.setMinimumHeight(60); self.ed_idea.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred); self.ed_idea.setPlaceholderText("Ý tưởng (2–3 dòng)")
        self.ed_idea.setObjectName('ed_idea')
        self.ed_product=QPlainTextEdit(); self.ed_product.setFont(FONT_INPUT); self.ed_product.setMinimumHeight(120); self.ed_product.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred); self.ed_product.setPlaceholderText("Nội dung chính / Đặc điểm sản phẩm")
        self.ed_product.setObjectName('ed_product')
        g.addWidget(QLabel("Tên dự án:"),0,0,1,1); g.addWidget(self.ed_name,1,0,1,1)
        g.addWidget(QLabel("Ý tưởng chính:"),2,0,1,1); g.addWidget(self.ed_idea,3,0,1,1)
        g.addWidget(QLabel("Nội dung / Đặc điểm:"),4,0,1,1); g.addWidget(self.ed_product,5,0,1,1)
        for w in gb_proj.findChildren(QLabel): w.setFont(FONT_LABEL)
        self.left.addWidget(gb_proj)

        gb_models=QGroupBox("Thông tin người mẫu / diễn viên"); _groupbox(gb_models); mv=QVBoxLayout(gb_models); mv.setSpacing(6)
        bar=QHBoxLayout(); header=QLabel("Thông tin người mẫu"); header.setFont(FONT_LABEL)
        btn_add=QToolButton(); btn_add.setText("+"); btn_add.clicked.connect(self._add_model_row)
        btn_rm=QToolButton(); btn_rm.setText("−"); btn_rm.clicked.connect(lambda:self._remove_model_row(None))
        bar.addWidget(header); bar.addStretch(1); bar.addWidget(btn_add); bar.addWidget(btn_rm); mv.addLayout(bar)
        self.models_area=QScrollArea(); self.models_area.setWidgetResizable(True); self.models_area.setFixedHeight(220)
        self.models_root=QWidget(); self.models_layout=QVBoxLayout(self.models_root); self.models_layout.setContentsMargins(6,6,6,6); self.models_layout.setSpacing(10)
        self.models_area.setWidget(self.models_root); mv.addWidget(self.models_area)
        self.left.addWidget(gb_models)
        self._add_model_row()

        gb_prod=QGroupBox("Ảnh sản phẩm"); _groupbox(gb_prod)
        pl=QVBoxLayout(gb_prod); pl.setSpacing(6)
        self.prod_scroll=QScrollArea(); self.prod_scroll.setWidgetResizable(True); self.prod_scroll.setFixedHeight(PROD_IMG+28)
        self.grid_root=QWidget(); self.grid=QGridLayout(self.grid_root); self.grid.setContentsMargins(6,6,6,6); self.grid.setSpacing(6)
        self.prod_scroll.setWidget(self.grid_root); pl.addWidget(self.prod_scroll)
        self.left.addWidget(gb_prod)
        self._refresh_product_grid()

        gb_cfg=QGroupBox("Cài đặt video"); _groupbox(gb_cfg); s=QGridLayout(gb_cfg); s.setVerticalSpacing(6); s.setColumnStretch(1,1)
        def big(w):
            w.setMinimumHeight(32); w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed);
            return w
        self.cb_style=big(QComboBox()); self.cb_style.addItems(["Viral","KOC Review","Kể chuyện"])
        self.cb_imgstyle=big(QComboBox()); self.cb_imgstyle.addItems(["Điện ảnh","Hiện đại/Trendy","Anime","Hoạt hình 3D"])
        self.cb_script_model=big(QComboBox()); self.cb_script_model.addItems(["Gemini 2.5 Flash (mặc định)","ChatGPT5 (tuỳ chọn)"]); self.cb_script_model.setCurrentIndex(0)
        self.cb_image_model=big(QComboBox()); self.cb_image_model.addItems(["Gemini","Whisk"])
        self.ed_voice=big(QLineEdit()); self.ed_voice.setFont(FONT_INPUT); self.ed_voice.setPlaceholderText("ElevenLabs VoiceID")
        self.sp_duration=big(QSpinBox()); self.sp_duration.setRange(8,1200); self.sp_duration.setSingleStep(8); self.sp_duration.setValue(32)
        self.lb_scenes=QLabel("Số cảnh: 4")
        self.sp_duration.valueChanged.connect(self._update_scenes)
        self.sp_videos=big(QSpinBox()); self.sp_videos.setRange(1,4); self.sp_videos.setValue(1)
        self.cb_ratio=big(QComboBox()); self.cb_ratio.addItems(["9:16","16:9","1:1","4:5"])
        self.cb_lang=big(QComboBox()); self.cb_lang.addItems(["vi","en"])
        self.cb_social=big(QComboBox()); self.cb_social.addItems(['TikTok','Facebook','YouTube'])
        self.cb_social.setObjectName('cb_social')
        s.setColumnStretch(1,1); s.setColumnStretch(3,1)
        s.addWidget(QLabel("Phong cách kịch bản:"),0,0); s.addWidget(self.cb_style,0,1); s.addWidget(QLabel("Phong cách hình ảnh:"),0,2); s.addWidget(self.cb_imgstyle,0,3)
        s.addWidget(QLabel("Model kịch bản:"),1,0); s.addWidget(self.cb_script_model,1,1); s.addWidget(QLabel("Model tạo ảnh:"),1,2); s.addWidget(self.cb_image_model,1,3)
        s.addWidget(QLabel("Lời thoại:"),2,0); s.addWidget(self.ed_voice,2,1); s.addWidget(QLabel("Ngôn ngữ thoại:"),2,2); s.addWidget(self.cb_lang,2,3)
        s.addWidget(QLabel("Thời lượng (giây):"),3,0); s.addWidget(self.sp_duration,3,1); s.addWidget(QLabel("Số video/cảnh:"),3,2); s.addWidget(self.sp_videos,3,3)
        s.addWidget(QLabel("Tỉ lệ khung hình:"),4,0); s.addWidget(self.cb_ratio,4,1); s.addWidget(QLabel("Nền tảng Social:"),4,2); s.addWidget(self.cb_social,4,3)
        for w in gb_cfg.findChildren(QLabel): w.setFont(FONT_LABEL)
        self.left.addWidget(gb_cfg)

        hb=QHBoxLayout()
        self.btn_script=QPushButton("Viết kịch bản"); self.btn_script.setStyleSheet('QPushButton{background:#1976D2;color:white;border-radius:8px;padding:8px 12px;font-weight:bold;font-size:14px;} QPushButton:hover{background:#1565C0;}')
        self.btn_run=QPushButton("Bắt đầu tạo video"); self.btn_run.setStyleSheet('QPushButton{background:#26A69A;color:white;border-radius:8px;padding:8px 12px;font-weight:bold;font-size:14px;} QPushButton:hover{background:#1E8E7E;}')
        self.btn_both=QPushButton("Viết & Tạo ngay"); self.btn_both.setStyleSheet('QPushButton{background:#0E7C66;color:white;border-radius:8px;padding:8px 12px;font-weight:bold;font-size:14px;} QPushButton:hover{background:#0C6B58;}')
        self.btn_export_prompts=QPushButton("Tải Prompt"); self.btn_export_previews=QPushButton("Tải ảnh xem trước")
        hb.addWidget(self.btn_script); hb.addWidget(self.btn_run); hb.addWidget(self.btn_both); hb.addWidget(self.btn_export_prompts); hb.addWidget(self.btn_export_previews); hb.addStretch(1)
        self.left.addLayout(hb)

        gb_script=QGroupBox("Kịch bản chi tiết"); _groupbox(gb_script)
        v1=QVBoxLayout(gb_script); self.ed_script=QPlainTextEdit(); self.ed_script.setFont(FONT_INPUT); v1.addWidget(self.ed_script); self.right.addWidget(gb_script,1)

        gb_cards=QGroupBox("Kết quả cảnh"); _groupbox(gb_cards)
        v2=QVBoxLayout(gb_cards); self.cards_area=QScrollArea(); self.cards_area.setWidgetResizable(True)
        self.cards_root=QWidget(); self.cards_layout=QVBoxLayout(self.cards_root); self.cards_layout.setContentsMargins(6,6,6,6); self.cards_layout.setSpacing(8)
        self.cards_area.setWidget(self.cards_root); v2.addWidget(self.cards_area); self.right.addWidget(gb_cards,2)

        gb_log=QGroupBox("Nhật ký xử lý"); _groupbox(gb_log)
        v3=QVBoxLayout(gb_log); self.ed_log=QPlainTextEdit(); self.ed_log.setFont(FONT_INPUT); self.ed_log.setReadOnly(True); v3.addWidget(self.ed_log); self.right.addWidget(gb_log,1)

        self.btn_script.clicked.connect(self._on_make_script)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_both.clicked.connect(self._on_both)
        self.btn_export_prompts.clicked.connect(self._export_prompts)
        self.btn_export_previews.clicked.connect(self._export_previews)

        self._update_scenes()

    def _add_model_row(self):
        if len(self.model_rows)>=5: return
        wrap=QFrame(); wrap.setFrameShape(QFrame.StyledPanel); wrap.setStyleSheet("QFrame{background:#F7FBFF;border:1px solid #D6EAF8;border-radius:6px;}")
        lay=QHBoxLayout(wrap); lay.setContentsMargins(8,8,8,8); lay.setSpacing(10)
        img=QLabel("Chọn ảnh"); img.setFixedSize(MODEL_IMG,MODEL_IMG); img.setAlignment(Qt.AlignCenter); img.setStyleSheet("border:1px dashed #B0BEC5;background:#FFFFFF;")
        img.mousePressEvent=lambda e,lab=img:self._pick_model_image(lab)
        box=QVBoxLayout()
        lab=QLabel("Mô tả người mẫu ( JSON/Text )"); lab.setFont(FONT_LABEL)
        ed=QPlainTextEdit(); ed.setFont(FONT_INPUT); ed.setMinimumHeight(80); ed.setMaximumHeight(MODEL_IMG); ed.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        box.addWidget(lab); box.addWidget(ed)
        delbtn=QToolButton(); delbtn.setText("X"); delbtn.setToolTip("Xoá người mẫu"); delbtn.clicked.connect(lambda:self._remove_model_row(wrap))
        lay.addWidget(img,0,Qt.AlignTop); lay.addLayout(box,1); lay.addWidget(delbtn,0,Qt.AlignTop)
        self.models_layout.addWidget(wrap); self.model_rows.append({"wrap":wrap,"img":img,"json":ed})

    def _remove_model_row(self,wrap):
        if not self.model_rows: return
        if wrap is None: wrap=self.model_rows[-1]["wrap"]
        for i,r in enumerate(self.model_rows):
            if r["wrap"] is wrap: self.model_rows.pop(i); wrap.setParent(None); break

    def _pick_model_image(self,label):
        path,_=QFileDialog.getOpenFileName(self,"Chọn ảnh người mẫu","","Images (*.png *.jpg *.jpeg *.webp)")
        if not path: return
        label.setPixmap(QPixmap(path).scaled(MODEL_IMG,MODEL_IMG,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        label.setStyleSheet("border:1px solid #90CAF9;background:#FFFFFF;")
        label.setProperty("path",path)

    def _refresh_product_grid(self):
        while getattr(self,'grid',None) and self.grid.count():
            it=self.grid.takeAt(0); w=it.widget();
            if w: w.deleteLater()
        r=c=0; max_cols=6
        for p in self.prod_paths:
            lb=QLabel(); lb.setFixedSize(PROD_IMG,PROD_IMG); lb.setAlignment(Qt.AlignCenter); lb.setStyleSheet("border:1px solid #90CAF9;background:#FFFFFF;")
            lb.setPixmap(QPixmap(p).scaled(PROD_IMG,PROD_IMG,Qt.KeepAspectRatio,Qt.SmoothTransformation)); self.grid.addWidget(lb,r,c); c+=1
            if c>=max_cols: c=0; r+=1
        tile=QLabel("＋ Thêm ảnh (PNG/JPG/WebP)"); tile.setFixedSize(PROD_IMG,PROD_IMG); tile.setAlignment(Qt.AlignCenter); tile.setStyleSheet("border:1px dashed #B0BEC5;background:#FAFAFA;")
        def _pick(_):
            files,_=QFileDialog.getOpenFileNames(self,"Chọn ảnh sản phẩm","","Images (*.png *.jpg *.jpeg *.webp)")
            if not files: return
            self.prod_paths.extend(files); self._refresh_product_grid()
        tile.mousePressEvent=_pick
        self.grid.addWidget(tile,r,c)

    def _update_scenes(self):
        n=max(1, math.ceil(self.sp_duration.value()/8.0)); self.lb_scenes.setText(f"Số cảnh: {n}")

    def _collect_cfg(self):
        first_model_json=""
        if self.model_rows:
            try: first_model_json=self.model_rows[0]["json"].toPlainText()
            except Exception: first_model_json=""
        return {"project_name":(self.ed_name.text() or '').strip() or svc.default_project_name(),
                "idea":self.ed_idea.toPlainText(),"product_main":self.ed_product.toPlainText(),
                "script_style":self.cb_style.currentText(),"image_style":self.cb_imgstyle.currentText(),
                "script_model":self.cb_script_model.currentText(),"image_model":self.cb_image_model.currentText(),
                "voice_id":self.ed_voice.text().strip(),"duration_sec":int(self.sp_duration.value()),
                "videos_count":int(self.sp_videos.value()),"ratio":self.cb_ratio.currentText(),"speech_lang":self.cb_lang.currentText(),
                "first_model_json":first_model_json}

    def _append_log(self,msg):
        ts=datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"); line=f"[{ts}] {msg}"; self.ed_log.appendPlainText(line)
        try: dirs=svc.ensure_project_dirs(self.ed_name.text().strip() or svc.default_project_name()); open(dirs["log"],"a",encoding="utf-8").write(line+"\n")
        except Exception: pass

    def _on_make_script(self):
        cfgv=self._collect_cfg()
        try:
            outline=sscript.build_outline(cfgv)
        except MissingAPIKey:
            QMessageBox.warning(self,"Thiếu API Key","Chưa nhập Google API Key trong tab Cài đặt."); self._append_log("Thiếu Google API Key → Không thể sinh kịch bản."); return
        except Exception as e:
            QMessageBox.critical(self,"Lỗi Gemini",str(e)); self._append_log(f"Lỗi Gemini: {e}"); return
        self.last_outline=outline; self.ed_script.setPlainText(outline.get("screenplay_text",""))
        self._rebuild_cards(outline.get("scenes",[])); self._append_log("Đã sinh kịch bản & prompt (Gemini 2.5 Flash).")

    def _rebuild_cards(self,scenes):
        while self.cards_layout.count():
            it=self.cards_layout.takeAt(0); w=it.widget();
            if w: w.deleteLater()
        self.cards={}
        for sc in scenes:
            card=QGroupBox(f"Cảnh {sc.get('index')}"); card.setStyleSheet('QGroupBox{font-weight:bold;font-size:15px;color:#0D47A1;border:1px solid #BBDEFB;border-radius:8px;margin-top:6px;padding:8px;}')
            gl=QGridLayout(card); gl.setVerticalSpacing(6)
            img=QLabel(); img.setFixedSize(PROD_IMG,PROD_IMG); img.setAlignment(Qt.AlignCenter); img.setStyleSheet("border:1px dashed #B0BEC5;background:#FFFFFF;")
            p=self.prod_paths[0] if self.prod_paths else None
            if not p and self.model_rows and self.model_rows[0]["img"].property("path"): p=self.model_rows[0]["img"].property("path")
            if p: img.setPixmap(QPixmap(p).scaled(PROD_IMG,PROD_IMG,Qt.KeepAspectRatio,Qt.SmoothTransformation)); img.setStyleSheet("border:1px solid #90CAF9;background:#FFFFFF;")
            desc=QPlainTextEdit(); desc.setFont(FONT_INPUT); desc.setPlainText(sc.get("desc","")); desc.setReadOnly(True)
            speech=QPlainTextEdit(); speech.setFont(FONT_INPUT); speech.setPlainText("Lời thoại: "+(sc.get("speech",""))); speech.setReadOnly(True)
            btn=QPushButton("Hiển thị Prompt"); btn.setStyleSheet('QPushButton{background:#E8EAF6;border:1px solid #9FA8DA;border-radius:8px;padding:4px 8px;}')
            pa=QPlainTextEdit(); pa.setFont(FONT_INPUT); pa.setPlainText(sc.get("prompt_image","")); pa.setVisible(False); pa.setReadOnly(True)
            btn.clicked.connect(lambda _,x=pa: x.setVisible(not x.isVisible()))
            gl.addWidget(img,0,0,3,1); gl.addWidget(QLabel("Mô tả cảnh:"),0,1); gl.addWidget(desc,1,1)
            gl.addWidget(speech,2,1); gl.addWidget(btn,3,0); gl.addWidget(pa,3,1)
            self.cards_layout.addWidget(card); self.cards[sc.get("index")]={"card":card,"img":img,"prompt":pa}
        self.cards_layout.addStretch(1)

    def _on_both(self):
        self._on_make_script()
        if self.last_outline: self._on_run()

    def _on_run(self):
        if not self.last_outline: QMessageBox.information(self,"Thiếu kịch bản","Vui lòng bấm 'Viết kịch bản' trước khi dựng video."); return
        cfgv=self._collect_cfg(); dirs=svc.ensure_project_dirs(cfgv["project_name"]); self._append_log("Bắt đầu gửi job dựng video sang Labs...")
        scenes=self.last_outline.get("scenes",[]); model_paths=[r["img"].property("path") for r in self.model_rows if hasattr(r["img"],"property") and r["img"].property("path")]; prod_paths=list(self.prod_paths or [])
        self.worker=_Worker(cfgv,scenes,model_paths,prod_paths,str(dirs["root"])); self.worker.startedSig.connect(lambda _ : self._set_busy(True)); self.worker.progress.connect(self._on_progress); self.worker.finished.connect(self._on_finished); self.worker.start()

    def _set_busy(self,busy:bool):
        for w in [self.btn_script,self.btn_run,self.btn_both,self.btn_export_prompts,self.btn_export_previews]: w.setEnabled(not busy)

    def _on_progress(self,job,info): self._append_log(f"Job {job.get('op')} scene={job.get('scene')} status={(info or {}).get('status','...')}")
    def _on_finished(self,done): self._append_log(f"Hoàn tất {len(done)} job."); self._set_busy(False)

    def _export_prompts(self):
        if not self.last_outline: QMessageBox.information(self,"Chưa có dữ liệu","Hãy viết kịch bản trước."); return
        cfgv=self._collect_cfg(); dirs=svc.ensure_project_dirs(cfgv["project_name"])
        for sc in self.last_outline.get("scenes",[]):
            fp=os.path.join(str(dirs["prompt"]), f"scene_{sc['index']}_prompt.txt"); open(fp,"w",encoding="utf-8").write(sc.get("prompt_image",""))
        self._append_log("Đã lưu prompt từng cảnh vào thư mục Prompt.")

    def _export_previews(self):
        if not self.last_outline: QMessageBox.information(self,"Chưa có dữ liệu","Hãy viết kịch bản trước."); return
        cfgv=self._collect_cfg(); dirs=svc.ensure_project_dirs(cfgv["project_name"])
        for idx,data in self.cards.items():
            pm=data["img"].pixmap()
            if pm: pm.save(os.path.join(str(dirs["preview"]), f"scene_{idx}_preview.png"),"PNG")
        self._append_log("Đã lưu ảnh xem trước vào thư mục Ảnh xem trước.")
# QSS_AUTOLOAD_V1
try:
    import os
    from PyQt5.QtWidgets import QApplication, QWidget
    def _qss_autoload_once(self):
        app = QApplication.instance()
        if app is None: return
        if getattr(app, '_vsu_qss_loaded', False): return
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qss_path = os.path.join(base, 'styles', 'app.qss')
            if os.path.exists(qss_path):
                with open(qss_path,'r',encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
                app._vsu_qss_loaded = True
        except Exception as _e:
            print('QSS autoload error:', _e)

    if 'VideoBanHangPanel' in globals():
        def _vsu_showEvent_qss(self, e):
            try: _qss_autoload_once(self)
            except Exception as _e: print('QSS load err:', _e)
            try: QWidget.showEvent(self, e)
            except Exception: pass
        VideoBanHangPanel.showEvent = _vsu_showEvent_qss
except Exception as _e:
    print('init QSS autoload error:', _e)
