import os, json, webbrowser, glob, time, shutil, re, datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QFileDialog, QSpinBox, QComboBox, QProgressBar,
    QSplitter, QAbstractItemView, QHeaderView, QApplication, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, QByteArray, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont

# Support both package and flat layouts
try:
    from utils.logger import Console
    from utils.config import load as load_cfg
except Exception:  # pragma: no cover
    from logger import Console
    from config import load as load_cfg

try:
    from services.labs_flow_service import LabsClient, DEFAULT_PROJECT_ID
except Exception:  # pragma: no cover
    from labs_flow_service import LabsClient, DEFAULT_PROJECT_ID

def safe_name(s: str)->str:
    s = s or ""
    s = s.lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "project"

BASE_COLS = ["Dự án","Cảnh","Image","Prompt","Trạng thái"]
def _video_labels(n): return [f"Video {i+1}" for i in range(max(0,n))]
TAIL_COLS = ["Hoàn thành"]
IMAGE_GLOB = ("*.png","*.jpg","*.jpeg","*.webp","*.bmp")

def short_text(s, n=90):
    s=(s or "").replace("\n"," ").strip()
    return s if len(s)<=n else s[:n-1]+"…"

def parse_prompt_any(obj):
    scenes=[]
    def _to_text(p):
        if isinstance(p, str):
            return p
        try:
            return json.dumps(p, ensure_ascii=False)
        except Exception:
            return str(p)
    if isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict) and "prompt" in it:
                scenes.append(_to_text(it["prompt"]))
            else:
                scenes.append(_to_text(it))
    elif isinstance(obj, dict):
        if "scenes" in obj and isinstance(obj["scenes"], list):
            for it in obj["scenes"]:
                if isinstance(it, dict) and "prompt" in it:
                    scenes.append(_to_text(it["prompt"]))
                else:
                    scenes.append(_to_text(it))
        elif "prompt" in obj:
            scenes.append(_to_text(obj["prompt"]))
        else:
            scenes.append(_to_text(obj))
    return scenes

def parse_prompt_file(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            obj=json.load(f)
    except Exception:
        return []
    return parse_prompt_any(obj)

class SeqWorker(QObject):
    log = pyqtSignal(str,str)
    progress = pyqtSignal(int, str)
    row_update = pyqtSignal(int, dict)
    started = pyqtSignal()
    finished = pyqtSignal(int)
    def __init__(self, client, jobs, model, aspect, copies, project_id):
        super().__init__(); self.client=client; self.jobs=jobs; self.model=model; self.aspect=aspect; self.copies=copies; self.project_id=project_id
    def run(self):
        self.started.emit()
        total=max(1,len(self.jobs)); done=0
        for i,j in enumerate(self.jobs):
            if j.get("image_path"):
                self.log.emit("INFO", f"[{i+1}/{len(self.jobs)}] Upload ảnh…")
                self.progress.emit(int(done*100/total), f"Cảnh {i+1}/{len(self.jobs)}: upload…")
                if not j.get("media_id"):
                    try:
                        mid=self.client.upload_image_file(j["image_path"]); j["media_id"]=mid
                        self.log.emit("HTTP", f"UPLOAD OK mediaId={mid}")
                    except Exception as e:
                        self.log.emit("ERR", f"Upload lỗi: {e}")
                        j["status"]="UPLOAD_FAILED"; self.row_update.emit(i,j); continue
            self.log.emit("INFO", f"[{i+1}/{len(self.jobs)}] Start generate…")
            try:
                self.progress.emit(int(done*100/total), f"Cảnh {i+1}/{len(self.jobs)}: start…")
                rc=self.client.start_one(j, self.model, self.aspect, j.get("prompt",""), copies=self.copies, project_id=self.project_id)
                self.log.emit("HTTP", f"START OK -> {rc} ref(s).")
            except Exception as e:
                self.log.emit("ERR", f"Start thất bại: {e}")
            self.row_update.emit(i,j); done+=1; self.progress.emit(int(done*100/total), f"Đã gửi {done}/{len(self.jobs)} cảnh")
            time.sleep(1.2)
        self.progress.emit(100, "Hoàn tất gửi tuần tự"); self.finished.emit(1)

class CheckWorker(QObject):
    log = pyqtSignal(str,str); progress = pyqtSignal(int, str); row_update = pyqtSignal(int, dict); finished = pyqtSignal()
    def __init__(self, client, jobs): super().__init__(); self.client=client; self.jobs=jobs
    def run(self):
        names=[n for j in self.jobs for n in j.get("operation_names",[])]
        if not names: self.log.emit("INFO","[Check] chưa có operation."); self.finished.emit(); return
        self.progress.emit(0, "Đang check…")
        try:
            rs=self.client.batch_check_operations(names)
        except Exception as e:
            self.log.emit("ERR", f"Check lỗi: {e.__class__.__name__}: {e}"); self.finished.emit(); return
        total=max(1,len(self.jobs)); done=0
        for idx,j in enumerate(self.jobs):
            found=False
            for nm in j.get("operation_names",[]):
                if nm in rs:
                    v=rs[nm]; found=True
                    if v.get("video_urls"):
                        vids=v["video_urls"]; ci=j.get("op_index_map",{}).get(nm,0)
                        while len(j["video_by_idx"]) <= ci: j["video_by_idx"].append(None); j["thumb_by_idx"].append(None)
                        if not j["video_by_idx"][ci]: j["video_by_idx"][ci]=vids[0]
                        if v.get("image_urls"): j["thumb_by_idx"][ci]=v["image_urls"][0]
                    j["status"]=v.get("status","PROCESSING")
            if not found and j.get("status")=="PENDING": j["status"]="PROCESSING"
            self.row_update.emit(idx,j); done+=1; self.progress.emit(int(done*100/total), f"Đã check {done}/{len(self.jobs)} cảnh")
        self.log.emit("HTTP","Check xong."); self.finished.emit()

class ThumbWorker(QObject):
    done = pyqtSignal(int, int, object)
    def __init__(self, row, idx, url): super().__init__(); self.row=row; self.idx=idx; self.url=url
    def run(self):
        import requests
        try:
            r=requests.get(self.url, timeout=15); r.raise_for_status(); data=r.content
        except Exception:
            self.done.emit(self.row,self.idx,None); return
        pix=QPixmap(); pix.loadFromData(QByteArray(data))
        if not pix.isNull():
            pix=pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.done.emit(self.row,self.idx, QIcon(pix))
        else:
            self.done.emit(self.row,self.idx,None)

class DownloadWorker(QObject):
    log = pyqtSignal(str,str); progress = pyqtSignal(int, str); row_update = pyqtSignal(int, dict); finished = pyqtSignal(int,int, bool)
    def __init__(self, jobs, outdir, only_missing=True, expected_copies=1, project_name="project"):
        super().__init__(); self.jobs=jobs; self.outdir=outdir; self.only_missing=only_missing; self.expected_copies=expected_copies; self.project_name=project_name
    def run(self):
        os.makedirs(self.outdir, exist_ok=True)
        total=max(1,len(self.jobs)); done=0; ok=0; attempts=0
        all_success=True
        for idx,j in enumerate(self.jobs):
            vids=j.get("video_by_idx") or []
            if not vids: done+=1; self.progress.emit(int(done*100/total), f"Đã tải {ok}/{attempts}"); all_success=False; continue
            j.setdefault("downloaded_idx", set())
            for i,u in enumerate(vids, start=1):
                if not u: continue
                if self.only_missing and (i in j["downloaded_idx"]): continue
                attempts+=1
                base = f"{safe_name(self.project_name)}_canh_{j.get('scene_id','')}_video_{i}"
                dest=os.path.join(self.outdir, f"{base}.mp4")
                try:
                    import requests
                    with requests.get(u, stream=True, timeout=300, allow_redirects=True) as r:
                        r.raise_for_status(); open(dest,"wb").write(r.content)
                    j["downloaded_idx"].add(i); j.setdefault("local_paths",[]).append(dest); j["status"]="DOWNLOADED"; ok+=1
                    # nếu đủ số lượng video mong đợi -> set thời gian hoàn thành
                    if len(j["downloaded_idx"]) >= min(self.expected_copies, len(vids)):
                        j["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.log.emit("HTTP", f"Tải OK -> {dest}")
                except Exception as e:
                    self.log.emit("ERR", f"Tải thất bại: {u}")
                    all_success=False
            self.row_update.emit(idx,j); done+=1; self.progress.emit(int(done*100/total), f"Đã tải {ok}/{attempts}")
        self.finished.emit(ok, attempts, all_success)

class ProjectPanel(QWidget):
    project_completed = pyqtSignal(str)  # emit project_name when all videos downloaded
    run_all_requested = pyqtSignal()
    def __init__(self, project_name:str, base_dir:str, settings_provider=None, parent=None):
        super().__init__(parent)
        self.project_name=project_name; self.base_dir=base_dir; self.project_dir=os.path.join(base_dir, project_name)
        os.makedirs(self.project_dir, exist_ok=True)
        self.settings_provider = settings_provider or (lambda: load_cfg())
        self.tokens=[]; self.client=None; self.jobs=[]; self.max_videos=4
        self.scenes=[]; self.image_files=[]; self._seq_running=False
        self._build_ui(); self.console.info(f"Dự án '{project_name}' đã sẵn sàng.")
        self._timer=None

    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(8,8,8,8); root.setSpacing(6)
        split=QSplitter(Qt.Horizontal); root.addWidget(split,1)
        split.setSizes([320, 960])  # 1/4 vs 3/4

        # LEFT (1/4)
        left=QWidget(); lv=QVBoxLayout(left); lv.setSpacing(6)

        # Nhóm: Dự án
        lv.addWidget(QLabel("Dự án"))
        rowm=QHBoxLayout()
        self.ed_name=QLineEdit(self.project_name); self.ed_name.setReadOnly(True)
        self.btn_del_scene=QPushButton("Xóa cảnh đã chọn"); self.btn_del_scene.clicked.connect(self._delete_selected_scenes)
        self.btn_del_all=QPushButton("Xóa tất cả cảnh"); self.btn_del_all.clicked.connect(self._delete_all_scenes)
        rowm.addWidget(self.ed_name,1); lv.addLayout(rowm)
        rowx=QHBoxLayout(); rowx.addWidget(self.btn_del_scene); rowx.addWidget(self.btn_del_all); lv.addLayout(rowx)

        # Model/Aspect/Copies
        lv.addWidget(QLabel("Model / Tỉ lệ / Số video"))
        self.cb_model=QComboBox(); self.cb_model.addItems(["veo_3_1_i2v_s_fast_portrait_ultra","veo_3_1_i2v_s_fast_ultra","veo_3_1_i2v_s_portrait","veo_3_1_i2v_s","veo_3_1_t2v_fast_ultra","veo_3_1_t2v"])
        self.cb_aspect=QComboBox(); self.cb_aspect.addItems(["VIDEO_ASPECT_RATIO_PORTRAIT","VIDEO_ASPECT_RATIO_LANDSCAPE","VIDEO_ASPECT_RATIO_SQUARE"])
        self.sp_copies=QSpinBox(); self.sp_copies.setRange(1,12); self.sp_copies.setValue(4); self.sp_copies.valueChanged.connect(self._ensure_columns)
        rowcfg=QHBoxLayout(); rowcfg.addWidget(self.cb_model,1); rowcfg.addWidget(self.cb_aspect,1); rowcfg.addWidget(self.sp_copies,0)
        lv.addLayout(rowcfg)

        # Prompt: nhập hoặc nạp file
        lv.addWidget(QLabel("Prompt (nhập hoặc hiển thị từ file)"))
        self.ed_json=QTextEdit(); self.ed_json.setMinimumHeight(120); lv.addWidget(self.ed_json)
        rowp=QHBoxLayout(); btn_prompt=QPushButton("Chọn file prompt"); btn_prompt.clicked.connect(self._pick_prompt_file); rowp.addWidget(btn_prompt); lv.addLayout(rowp)

        # Ảnh: chọn thư mục hoặc chọn từng ảnh
        lv.addWidget(QLabel("Ảnh tham chiếu"))
        rowi=QHBoxLayout()
        btn_img_dir=QPushButton("Chọn thư mục ảnh"); btn_img_dir.clicked.connect(self._pick_image_dir); rowi.addWidget(btn_img_dir)
        btn_imgs=QPushButton("Chọn ảnh lẻ"); btn_imgs.clicked.connect(self._pick_images_multi); rowi.addWidget(btn_imgs)
        lv.addLayout(rowi)

        # Nút lớn bắt đầu
        self.btn_run=QPushButton("BẮT ĐẦU TẠO VIDEO"); self.btn_run.setMinimumHeight(46)
        self.btn_run.setStyleSheet("QPushButton{background:#1976d2;color:white;font-weight:700;font-size:17px;border-radius:8px;padding:12px;} QPushButton:hover{background:#1e88e5;}")
        self.btn_run.clicked.connect(self._run_seq)
        lv.addWidget(self.btn_run)

        self.btn_run_all=QPushButton("CHẠY TOÀN BỘ CÁC DỰ ÁN (THEO THỨ TỰ)")
        self.btn_run_all.setMinimumHeight(46)
        self.btn_run_all.setStyleSheet("QPushButton{background:#43a047;color:white;font-weight:700;font-size:16px;border-radius:8px;padding:12px;} QPushButton:hover{background:#2e7d32;}")
        self.btn_run_all.clicked.connect(lambda: self.run_all_requested.emit())
        lv.addWidget(self.btn_run_all)

        lv.addStretch(1)

        split.addWidget(left)

        # RIGHT (3/4)
        right=QWidget(); rv=QVBoxLayout(right)
        self.pb=QProgressBar(); self.pb.setFormat("%p%"); rv.addWidget(self.pb)
        self.pb_text=QLabel("Sẵn sàng"); rv.addWidget(self.pb_text)

        self.table=QTableWidget(0, 0)
        self.table.setWordWrap(False); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._open_cell)
        rv.addWidget(self.table, 1)

        self.console=Console(); self.console.setFixedHeight(160); rv.addWidget(self.console)
        split.addWidget(right)

        self._ensure_columns()

    def _ensure_columns(self):
        n=int(self.sp_copies.value())
        headers = BASE_COLS + _video_labels(n) + TAIL_COLS
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

    # Pickers
    def _pick_prompt_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Chọn prompt JSON", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                obj=json.load(f)
            self.scenes=parse_prompt_any(obj)
            self.ed_json.setPlainText(json.dumps(obj, ensure_ascii=False, indent=2))
            self.console.info(f"Đã nạp {len(self.scenes)} cảnh từ prompt.")
        except Exception as e:
            self.console.err(f"JSON không hợp lệ: {e}")

    def _pick_image_dir(self):
        d=QFileDialog.getExistingDirectory(self,"Chọn thư mục ảnh")
        if not d: return
        files=[]
        for pat in IMAGE_GLOB: files.extend(glob.glob(os.path.join(d, pat)))
        files.sort(); self.image_files=list(dict.fromkeys(files))  # unique & preserve order
        self.console.info(f"Đã nạp {len(self.image_files)} ảnh.")

    def _pick_images_multi(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Chọn ảnh", "", "Hình ảnh (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not paths: return
        self.image_files = list(dict.fromkeys(self.image_files + paths))
        self.console.info(f"Đã thêm {len(paths)} ảnh; tổng {len(self.image_files)}.")

    # Helpers
    def _on_event(self, ev):
        k=ev.get("kind")
        if k=="http_ok": self.console.http("HTTP 200")
        elif k=="http_other_err": self.console.err(f"HTTP {ev.get('code')}: {ev.get('detail','')}")

    def _settings(self):
        return (self.settings_provider() if callable(self.settings_provider) else load_cfg())

    def _project_paths(self):
        cfg = self._settings()
        root = cfg.get("download_root")
        if not root: root = os.path.join(os.path.expanduser("~"), "Downloads", "VeoProjects")
        proj_dir = os.path.join(root, self.project_name)
        dirs = {
            "root": root,
            "project": proj_dir,
            "prompts": os.path.join(proj_dir, "Prompt video"),
            "images": os.path.join(proj_dir, "Ảnh tham chiếu"),
            "videos": os.path.join(proj_dir, "Video"),
        }
        for d in dirs.values():
            if isinstance(d, str): os.makedirs(d, exist_ok=True)
        return dirs

    def _prepare_jobs(self):
        self.jobs=[]; self.table.setRowCount(0)
        # lấy scenes từ text box nếu chưa có
        if not self.scenes and self.ed_json.toPlainText().strip():
            try:
                obj=json.loads(self.ed_json.toPlainText())
                self.scenes=parse_prompt_any(obj)
            except Exception:
                self.scenes=[]

        scenes=self.scenes or []; imgs=self.image_files or []
        model_str = getattr(self.cb_model, "currentText", lambda: "")()
        is_t2v = "_t2v" in (model_str or "")

        if not scenes:
            self.console.warn("Chưa có kịch bản (JSON)."); return 0

        if not is_t2v and not imgs:
            self.console.warn("Chưa có ảnh tham chiếu."); return 0

        if is_t2v:
            n=len(scenes)
        else:
            n=min(len(scenes), len(imgs))
            if len(imgs)<len(scenes): self.console.warn(f"Số ảnh ({len(imgs)}) ít hơn số cảnh ({len(scenes)}); chỉ tạo {n} cảnh đầu.")

        copies=int(self.sp_copies.value())

        paths = self._project_paths()
        # Lưu prompt + copy ảnh vào thư mục dự án, đặt tên chuẩn
        for i in range(n):
            scene_id = i+1
            # prompt file
            prompt_text = scenes[i]
            prompt_filename = f"{safe_name(self.project_name)}_canh_{scene_id}_prompt.json"
            try:
                # nếu có thể parse -> lưu json đẹp
                obj=json.loads(prompt_text)
                open(os.path.join(paths["prompts"], prompt_filename), "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2))
            except Exception:
                open(os.path.join(paths["prompts"], prompt_filename.replace(".json",".txt")), "w", encoding="utf-8").write(prompt_text)

            # image copy
            if not is_t2v:
                src = imgs[i]
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                img_filename = f"{safe_name(self.project_name)}_canh_{scene_id}_anh{ext}"
                dst = os.path.join(paths["images"], img_filename)
                try:
                    if os.path.abspath(src) != os.path.abspath(dst):
                        shutil.copy2(src, dst)
                except Exception as e:
                    self.console.err(f"Không thể copy ảnh: {e}")
                    dst = src
            else:
                dst = None

            row=self.table.rowCount(); self.table.insertRow(row)
            job={"scene_id":f"{scene_id}","prompt":prompt_text,"image_path":dst,"image_name":os.path.basename(dst) if dst else "",
                 "media_id":None,"operation_names":[],"status":"NEW","video_by_idx":[None]*copies,"thumb_by_idx":[None]*copies,"op_index_map":{},
                 "downloaded_idx":set(),"thumb_icons":{},"completed_at":""}
            self.jobs.append(job); self._refresh_row(row, job)
        if n==0: self.console.warn("Không có cặp (prompt, ảnh) nào.")
        return n

    def _set_cell(self, row, col, text, tooltip=None, icon=None):
        it=self.table.item(row,col)
        if it is None: it=QTableWidgetItem(text); self.table.setItem(row,col,it)
        else: it.setText(text)
        if tooltip is not None: it.setToolTip(tooltip)
        if icon is not None: it.setIcon(icon)

    def _refresh_row(self, idx, job):
        col = 0
        self._set_cell(idx,col,self.project_name); col+=1
        self._set_cell(idx,col,str(job.get("scene_id",""))); col+=1
        self._set_cell(idx,col,job.get("image_name","")); col+=1
        self._set_cell(idx,col,short_text(job.get("prompt",""))); col+=1
        self._set_cell(idx,col,job.get("status","")); col+=1
        vids=job.get("video_by_idx") or []; thumbs=job.get("thumb_by_idx") or []
        for i in range(len(vids)):
            label=f"Video {i+1}"
            if vids[i]:
                if i+1 in job.get("downloaded_idx", set()): label+=" ✓"
                icon=job["thumb_icons"].get(i)
                if not icon and i < len(thumbs) and thumbs[i]: self._load_thumb_async(idx, i, thumbs[i])
                self._set_cell(idx, col+i, label, tooltip=vids[i], icon=icon)
            else: self._set_cell(idx, col+i, "")
        col += len(vids)
        self._set_cell(idx,col, job.get("completed_at",""))

    def _load_thumb_async(self, row, idx, url):
        th=QThread(self); w=ThumbWorker(row, idx, url); w.moveToThread(th)
        th.started.connect(w.run); w.done.connect(self._on_thumb); w.done.connect(th.quit); w.done.connect(w.deleteLater); th.finished.connect(th.deleteLater); th.start()

    def _on_thumb(self, row, idx, icon):
        if 0 <= row < len(self.jobs) and icon:
            self.jobs[row]["thumb_icons"][idx]=icon; self._refresh_row(row, self.jobs[row])

    # Actions
    def _ensure_client(self):
        cfg = self._settings()
        toks = [t.strip() for t in cfg.get("tokens", []) if t.strip()]
        if not toks:
            QMessageBox.warning(self, "Thiếu token", "Vào tab Cài đặt để nhập token trước khi chạy.")
            return False
        if not self.client:
            self.client = LabsClient(toks, on_event=self._on_event)
        return True

    def _run_seq(self):
        try:
            if not self._ensure_client(): return
            if not self.scenes and self.ed_json.toPlainText().strip():
                try:
                    obj=json.loads(self.ed_json.toPlainText())
                    self.scenes=parse_prompt_any(obj)
                except Exception:
                    pass
            n=self._prepare_jobs()
            if n<=0: return
            cfg = self._settings()
            model=self.cb_model.currentText(); aspect=self.cb_aspect.currentText(); copies=int(self.sp_copies.value()); pid=cfg.get("default_project_id") or DEFAULT_PROJECT_ID
            if self._seq_running: self.console.warn("Đang chạy tuần tự, vui lòng chờ…"); return
            self._seq_running=True
            self.btn_run.setEnabled(False); self.btn_run.setText("ĐANG TẠO…"); QApplication.setOverrideCursor(Qt.WaitCursor)
            self.pb.setValue(0); self.pb_text.setText(f"Bắt đầu: {n} cảnh, {copies} video/cảnh")
            self.console.info(f"Bắt đầu gửi tuần tự {n} cảnh; copies={copies}.")
            self._t=QThread(self)
            self._w=SeqWorker(self.client,self.jobs,model,aspect,copies,pid)
            self._w.moveToThread(self._t)
            self._t.started.connect(self._w.run)
            self._w.progress.connect(self._on_prog); self._w.row_update.connect(self._refresh_row)
            self._w.log.connect(lambda lv,msg: getattr(self.console, lv.lower())(msg) if hasattr(self.console, lv.lower()) else self.console.info(msg))
            def on_finish(_):
                self.console.info("Đã gửi xong theo tuần tự.")
                self.btn_run.setEnabled(True); self.btn_run.setText("BẮT ĐẦU TẠO VIDEO"); QApplication.restoreOverrideCursor()
                self.pb_text.setText("Hoàn tất gửi.")
                self._seq_running=False
                # start auto-check (hidden) mỗi 10s
                if not self._timer:
                    self._timer=QTimer(self); self._timer.setInterval(10000); self._timer.timeout.connect(self._check)
                self._timer.start()
            self._w.finished.connect(on_finish); self._w.finished.connect(self._t.quit); self._w.finished.connect(self._w.deleteLater); self._t.finished.connect(self._t.deleteLater); self._t.start()
        except Exception as e:
            self.console.err(f"Lỗi khởi chạy: {e}")
            try: QApplication.restoreOverrideCursor(); self.btn_run.setEnabled(True); self.btn_run.setText("BẮT ĐẦU TẠO VIDEO"); self._seq_running=False
            except Exception: pass

    def _on_prog(self, v, t): self.pb.setValue(v); self.pb_text.setText(t)

    def _all_downloaded(self):
        # true nếu mọi cảnh đều đã có đủ số video & được download
        exp = int(self.sp_copies.value())
        for j in self.jobs:
            vids = j.get("video_by_idx") or []
            if len([u for u in vids if u]) < exp: return False
            if len(j.get("downloaded_idx", set())) < exp: return False
        return True

    def _check(self):
        if not getattr(self,"client",None) or not self.jobs: return
        self._t2=QThread(self); self._w2=CheckWorker(self.client,self.jobs); self._w2.moveToThread(self._t2)
        self._t2.started.connect(self._w2.run); self._w2.progress.connect(self._on_prog); self._w2.row_update.connect(self._refresh_row)
        self._w2.log.connect(lambda lv,msg: getattr(self.console, lv.lower())(msg) if hasattr(self.console, lv.lower()) else self.console.info(msg))
        def on_finished():
            # auto-download về thư mục dự án/<Video>
            out = self._project_paths()["videos"]
            self._download(True, out)
        self._w2.finished.connect(on_finished); self._w2.finished.connect(self._t2.quit); self._w2.finished.connect(self._w2.deleteLater); self._t2.finished.connect(self._t2.deleteLater); self._t2.start()

    def _download(self, only_missing, outdir):
        self._t3=QThread(self); self._w3=DownloadWorker(self.jobs,outdir,only_missing=only_missing, expected_copies=int(self.sp_copies.value()), project_name=self.project_name); self._w3.moveToThread(self._t3)
        self._t3.started.connect(self._w3.run); self._w3.progress.connect(self._on_prog); self._w3.row_update.connect(self._refresh_row)
        self._w3.log.connect(lambda lv,msg: getattr(self.console, lv.lower())(msg) if hasattr(self.console, lv.lower()) else self.console.info(msg))
        def on_done(ok, attempts, all_success):
            if all_success and self._all_downloaded():
                # stop checking + phát tín hiệu hoàn tất dự án
                if self._timer: self._timer.stop()
                self.console.info("Đã tải xong toàn bộ video. Dừng kiểm tra.")
                self.project_completed.emit(self.project_name)
        self._w3.finished.connect(on_done); self._w3.finished.connect(self._t3.quit); self._w3.finished.connect(self._w3.deleteLater); self._t3.finished.connect(self._t3.deleteLater); self._t3.start()

    def _open_cell(self, row, col):
        # col==3 (Prompt) -> mở dialog xem đầy đủ
        if row>=len(self.jobs): return
        if col==3:
            full = self.jobs[row].get("prompt","")
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            dlg=QDialog(self); dlg.setWindowTitle(f"Prompt — Cảnh {self.jobs[row].get('scene_id','')}"); vv=QVBoxLayout(dlg)
            t=QTextEdit(); t.setReadOnly(True); t.setText(full); t.setFont(QFont("Courier New", 10)); vv.addWidget(t)
            btn=QPushButton("Đóng"); btn.clicked.connect(dlg.accept); vv.addWidget(btn, alignment=Qt.AlignRight)
            dlg.resize(720,480); dlg.exec_(); return
        # video cell -> mở link
        # columns: 0:Dự án,1:Cảnh,2:Image,3:Prompt,4:Trạng thái, [video cols], last:Hoàn thành
        first_video_col = 5
        last_col = self.table.columnCount()-1
        if first_video_col <= col < last_col:
            idx=col-first_video_col
            vids=self.jobs[row].get("video_by_idx") or []
            if idx>=len(vids): return
            url=vids[idx]
            if not url: return
            try: webbrowser.open(url)
            except Exception: pass

    def _delete_selected_scenes(self):
        sel = self.table.selectedItems()
        rows = sorted(set(it.row() for it in sel), reverse=True)
        for r in rows:
            if 0 <= r < len(self.jobs):
                self.table.removeRow(r)
                self.jobs.pop(r, None)
        self.console.info(f"Đã xóa {len(rows)} cảnh đã chọn.")

    def _delete_all_scenes(self):
        self.jobs.clear()
        self.table.setRowCount(0)
        self.console.info("Đã xóa toàn bộ cảnh.")

    def closeEvent(self, e):
        try:
            if self._timer: self._timer.stop()
        finally:
            e.accept()
