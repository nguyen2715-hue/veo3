
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt

class Console(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(4)
        self.view = QTextEdit(); self.view.setReadOnly(True)
        v.addWidget(self.view)
    def _w(self, lvl, msg):
        self.view.append(f"[{lvl}] {msg}")
    def info(self, msg): self._w("INFO", msg)
    def warn(self, msg): self._w("WARN", msg)
    def err(self, msg):  self._w("ERR", msg)
    def http(self, msg): self._w("HTTP", msg)
