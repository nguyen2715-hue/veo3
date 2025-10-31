import sys, os
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QListWidget, QSplitter, QLabel, QTabWidget
from PyQt5.QtCore import Qt
try:
    from ui.project_panel import ProjectPanel
    from ui.settings_panel import SettingsPanel
except Exception:
    from project_panel import ProjectPanel
    from settings_panel import SettingsPanel
try:
    from utils.config import load as load_cfg
except Exception:
    from config import load as load_cfg

class ProjectsPane(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._projects = {}
        self._queue_running = False
        # Always ensure at least one project exists so the right pane is visible immediately
        self._ensure_default_project()

    def _build_ui(self):
        root=QHBoxLayout(self); root.setContentsMargins(8,8,8,8); root.setSpacing(8)
        split=QSplitter(Qt.Horizontal); root.addWidget(split,1)
        split.setSizes([280, 1040])

        # Left column (project management) — 1/4 handled by parent panels, but here for list
        left=QWidget(); lv=QVBoxLayout(left)
        self.ed_name=QLineEdit(); self.ed_name.setPlaceholderText("Tên dự án…")
        self.btn_add=QPushButton("Thêm dự án"); self.btn_add.clicked.connect(self._add_project)
        self.btn_del=QPushButton("Xóa dự án"); self.btn_del.clicked.connect(self._del_project)
        self.btn_run_all=QPushButton("CHẠY TẤT CẢ (THEO THỨ TỰ)")
        self.btn_run_all.setMinimumHeight(44)
        self.btn_run_all.setStyleSheet("QPushButton{background:#43a047;color:white;font-weight:700;font-size:15px;border-radius:8px;padding:10px;} QPushButton:hover{background:#2e7d32;}")
        self.btn_run_all.clicked.connect(self._run_all_queue)
        lv.addWidget(QLabel("Quản lý dự án")); lv.addWidget(self.ed_name); lv.addWidget(self.btn_add); lv.addWidget(self.btn_del); self.list=QListWidget(); self.list.currentTextChanged.connect(self._switch_project); lv.addWidget(self.list,1)
        split.addWidget(left)

        self.right_holder=QWidget(); self.right_layout=QVBoxLayout(self.right_holder); split.addWidget(self.right_holder)

    def _add_project(self):
        name=self.ed_name.text().strip() or "Project"
        if name in self._projects: name=f"{name}_{len(self._projects)+1}"
        panel=ProjectPanel(name, self._default_root(), settings_provider=load_cfg, parent=self); panel.project_completed.connect(self._on_project_completed); panel.run_all_requested.connect(self._run_all_queue)
        self._projects[name]=panel; self.list.addItem(name); self.list.setCurrentRow(self.list.count()-1)

    def _del_project(self):
        it=self.list.currentItem()
        if not it: return
        name=it.text()
        panel=self._projects.pop(name, None)
        if panel: panel.setParent(None); panel.deleteLater()
        self.list.takeItem(self.list.currentRow())
        self._maybe_auto_add_after_delete()

    def _switch_project(self, name:str):
        while self.right_layout.count():
            item=self.right_layout.takeAt(0); w=item.widget()
            if w: w.setParent(None)
        panel=self._projects.get(name)
        if panel: self.right_layout.addWidget(panel)

    def _default_root(self):
        cfg = load_cfg()
        root = cfg.get("download_root")
        if not root: root = os.path.join(os.path.expanduser("~"), "Downloads", "VeoProjects")
        os.makedirs(root, exist_ok=True)
        return root


    def _ensure_default_project(self):
        if not self._projects:
            # Create a default project immediately so users don't need to click 'Thêm dự án'
            self.ed_name.setText("Project")
            self._add_project()

    def _maybe_auto_add_after_delete(self):
        if not self._projects:
            self._ensure_default_project()

    def _run_all_queue(self):
        # Start from the first project in list
        if not self._projects or self._queue_running:
            return
        self._queue_running = True
        self.btn_run_all.setEnabled(False)
        first = self.list.item(0).text() if self.list.count() else None
        if first:
            self.list.setCurrentRow(0)
            panel = self._projects.get(first)
            if panel: panel._run_seq()

    def _on_project_completed(self, project_name: str):
        if not self._queue_running:
            # even nếu user chạy thủ công, vẫn tiếp tục dự án kế tiếp theo yêu cầu
            self._queue_running = True
        # find next
        names = [self.list.item(i).text() for i in range(self.list.count())]
        if project_name in names:
            idx = names.index(project_name) + 1
            if idx < len(names):
                nxt = self._projects.get(names[idx])
                if nxt:
                    self.list.setCurrentRow(idx)
                    nxt._run_seq()
                    return
        # no more
        self._queue_running = False
        self.btn_run_all.setEnabled(True)

class MainWindow(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Super Ultra ")
        self.resize(1360,860)
        # tabs
        self.settings = SettingsPanel(self); self.addTab(self.settings, "Cài đặt")
        self.projects = ProjectsPane(); self.addTab(self.projects, "Image2Video")

        # --- v0.7.5 tabs ---
        try:
            from ui.text2video_panel import Text2VideoPane
            self.text2v = Text2VideoPane(parent=self)
            self.addTab(self.text2v, "Text2Video")
        except Exception as e:
            print("Text2Video tab error:", e)

        try:
            from ui.video_ban_hang_panel import VideoBanHangPanel
            self.ads = VideoBanHangPanel(parent=self)
            self.addTab(self.ads, "Video bán hàng")
        except Exception as e:
            print("Ads tab error:", e)

def main():
    app=QApplication(sys.argv)
    
    # Apply unified Material Design theme
    try:
        from ui.styles.unified_theme import apply_theme
        apply_theme(app)
    except Exception as e:
        print(f"Warning: Could not apply unified theme: {e}")
    
    w=MainWindow(); w.show(); sys.exit(app.exec_())

if __name__=='__main__':
    main()
