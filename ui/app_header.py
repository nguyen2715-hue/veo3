# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont

class AppHeader(QWidget):
    def __init__(self,_provider, parent=None):
        super().__init__(parent)
        self._get_=_provider
        v = QVBoxLayout(self); v.setContentsMargins(8, 8, 8, 8); v.setSpacing(0)
        self.lb_app = QLabel("Video Super Ultra")
        self.lb_ver = QLabel(f": V{self._}")
        f_app = QFont(); f_app.setPixelSize(14); f_app.setBold(True)
        f_ver = QFont(); f_ver.setPixelSize(14)
        self.lb_app.setFont(f_app); self.lb_ver.setFont(f_ver)
        v.addWidget(self.lb_app)
        v.addWidget(self.lb_ver)
        self.setStyleSheet("AppHeader{background:#FAFAFF;border-bottom:1px solid #B3E5FC;} QLabel{color:#1B1B1B;}")
    def refresh(self):
        self.lb_ver.setText(f": V{self._}")
