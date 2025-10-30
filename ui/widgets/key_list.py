# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit, QFileDialog)
from PyQt5.QtGui import QFont
from services import key_check_service as kcs
import datetime

FONT_TITLE = QFont(); FONT_TITLE.setPixelSize(14); FONT_TITLE.setBold(True)
FONT_LABEL = QFont(); FONT_LABEL.setPixelSize(13)
FONT_TEXT  = QFont(); FONT_TEXT.setPixelSize(12)

def _ts(): return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
def _mask(s:str)->str:
    s=(s or '').strip()
    if len(s)<=16: return s
    return s[:8] + '...' + s[-8:]

class _KeyItem(QWidget):
    def __init__(self, kind:str, key:str):
        super().__init__()
        self.kind=kind; self.key=(key or '').strip()
        h=QHBoxLayout(self); h.setContentsMargins(6,4,6,4); h.setSpacing(8)
        self.lb_key=QLabel(_mask(self.key)); self.lb_key.setFont(FONT_TEXT)
        self.lb_status=QLabel(''); self.lb_status.setFont(FONT_TEXT)
        self.btn_test=QPushButton('Kiểm tra Kết nối'); self.btn_test.setStyleSheet('QPushButton{background:#DDEBFF;border:1px solid #90CAF9;border-radius:8px;padding:4px 8px;}')
        self.btn_del=QPushButton('🗑'); self.btn_del.setFixedWidth(32)
        h.addWidget(self.lb_key); h.addStretch(1); h.addWidget(self.btn_test); h.addWidget(self.lb_status); h.addWidget(self.btn_del)
        self.btn_test.clicked.connect(self._on_test)
    def _on_test(self):
        ok,msg=kcs.check(self.kind, self.key)
        self.lb_status.setText(('✓ ' if ok else '✗ ')+msg)

class KeyList(QWidget):
    def __init__(self, *, title:str, kind:str, initial=None):
        super().__init__()
        self.kind=kind; initial=initial or []
        v=QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(6)
        self.lb_title=QLabel(title); self.lb_title.setFont(FONT_TITLE)
        self.lb_title.setStyleSheet('QLabel{background:#F5F9FF;border:1px solid #90CAF9;border-radius:8px;padding:6px 10px;}')
        v.addWidget(self.lb_title)
        self.listw=QListWidget(); v.addWidget(self.listw)
        row=QHBoxLayout()
        self.ed_new=QLineEdit(); self.ed_new.setFont(FONT_TEXT); self.ed_new.setPlaceholderText('Dán API Key của bạn vào đây')
        self.btn_add=QPushButton('Thêm Key'); self.btn_add.setStyleSheet('QPushButton{background:#1976D2;color:white;border-radius:8px;padding:6px 10px;} QPushButton:hover{background:#1565C0;}')
        self.btn_add.clicked.connect(self._add_from_input)
        row.addWidget(self.ed_new); row.addWidget(self.btn_add); v.addLayout(row)
        actions=QHBoxLayout()
        self.btn_import=QPushButton('Nhập từ File (.txt)'); self.btn_import.setStyleSheet('QPushButton{background:#E0F2F1;border:1px solid #80CBC4;border-radius:8px;padding:6px 10px;}')
        self.btn_test_all=QPushButton('Kiểm tra tất cả'); self.btn_test_all.setStyleSheet('QPushButton{background:#E8EAF6;border:1px solid #9FA8DA;border-radius:8px;padding:6px 10px;}')
        self.btn_import.clicked.connect(self._import_txt); self.btn_test_all.clicked.connect(self._test_all)
        actions.addWidget(self.btn_import); actions.addWidget(self.btn_test_all); actions.addStretch(1); v.addLayout(actions)
        self.set_keys(initial)
    def set_keys(self, keys):
        self.listw.clear(); seen=set()
        for k in (keys or []):
            k=(k or '').strip()
            if not k or k in seen: continue
            seen.add(k); self._add_item(k)
    def get_keys(self):
        out=[]
        for i in range(self.listw.count()):
            w=self.listw.itemWidget(self.listw.item(i))
            if w and w.key: out.append(w.key)
        return out
    def _add_item(self, key:str):
        it=QListWidgetItem(self.listw)
        w=_KeyItem(self.kind, key)
        self.listw.setItemWidget(it, w); it.setSizeHint(w.sizeHint())
        def _del(): self.listw.takeItem(self.listw.row(it))
        w.btn_del.clicked.connect(_del)
    def _add_from_input(self):
        key=(self.ed_new.text() or '').strip()
        if key and key not in set(self.get_keys()):
            self._add_item(key)
        self.ed_new.clear()
    def _import_txt(self):
        path,_=QFileDialog.getOpenFileName(self, 'Chọn file .txt', '', 'Text Files (*.txt)')
        if not path: return
        try:
            with open(path,'r',encoding='utf-8') as f:
                lines=[x.strip() for x in f.read().splitlines() if x.strip()]
            cur=set(self.get_keys())
            for k in lines:
                if k not in cur: self._add_item(k); cur.add(k)
        except Exception: pass
    def _test_all(self):
        for i in range(self.listw.count()):
            w=self.listw.itemWidget(self.listw.item(i))
            if w: w._on_test()
