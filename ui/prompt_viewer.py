
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QWidget, QTabWidget
from PyQt5.QtCore import Qt

class PromptViewer(QDialog):
    def __init__(self, prompt_json:str, dialogues=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết Cảnh")
        self.resize(860, 560)
        lay=QVBoxLayout(self)

        tabs=QTabWidget()
        # Tab Prompt JSON
        w1=QWidget(); l1=QVBoxLayout(w1); ed1=QTextEdit(); ed1.setReadOnly(True); ed1.setPlainText(prompt_json); l1.addWidget(ed1)
        tabs.addTab(w1,"Prompt JSON")
        # Tab Lời thoại
        w2=QWidget(); l2=QVBoxLayout(w2); ed2=QTextEdit(); ed2.setReadOnly(True)
        if dialogues:
            try:
                lines = ["- {speaker}: {vi} / {tgt}".format(speaker=d.get("speaker","?"), vi=d.get("text_vi",""), tgt=d.get("text_tgt","")) for d in dialogues]
                ed2.setPlainText("\n".join(lines))
            except Exception:
                ed2.setPlainText("(Không có lời thoại)")
        else:
            ed2.setPlainText("(Không có lời thoại)")
        l2.addWidget(ed2); tabs.addTab(w2,"Lời thoại")
        lay.addWidget(tabs)

        hb=QHBoxLayout()
        btn=QPushButton("Đóng"); btn.clicked.connect(self.accept)
        hb.addStretch(1); hb.addWidget(btn)
        lay.addLayout(hb)
