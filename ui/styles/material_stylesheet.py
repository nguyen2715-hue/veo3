# -*- coding: utf-8 -*-
"""
Material Design Light Theme Stylesheet
Blue (#2196F3) primary color with clean, modern look
"""

MATERIAL_LIGHT_STYLESHEET = """
/* ===== GLOBAL ===== */
QWidget {
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #FAFAFA;
}

/* ===== BUTTONS ===== */
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #1565C0;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #9E9E9E;
}

/* Secondary button style */
QPushButton[class="secondary"] {
    background-color: transparent;
    color: #2196F3;
    border: 1px solid #2196F3;
}

QPushButton[class="secondary"]:hover {
    background-color: #E3F2FD;
}

QPushButton[class="secondary"]:pressed {
    background-color: #BBDEFB;
}

/* ===== INPUT FIELDS ===== */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 8px;
    color: #212121;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 2px solid #2196F3;
    padding: 7px;
}

QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {
    background-color: #F5F5F5;
    color: #9E9E9E;
}

/* ===== COMBO BOX ===== */
QComboBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 28px;
}

QComboBox:focus {
    border: 2px solid #2196F3;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #757575;
    margin-right: 5px;
}

QComboBox:hover {
    border-color: #BDBDBD;
}

QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #E0E0E0;
    selection-background-color: #E3F2FD;
    selection-color: #1976D2;
    outline: none;
}

/* ===== SPIN BOX ===== */
QSpinBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 6px;
    min-height: 28px;
}

QSpinBox:focus {
    border: 2px solid #2196F3;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: transparent;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #F5F5F5;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #757575;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #757575;
}

/* ===== GROUP BOX (CARDS) ===== */
QGroupBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 500;
    color: #424242;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: #2196F3;
    background-color: white;
}

/* ===== TAB WIDGET ===== */
QTabWidget::pane {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    top: -1px;
}

QTabBar::tab {
    background-color: #F5F5F5;
    color: #757575;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 80px;
}

QTabBar::tab:selected {
    background-color: white;
    color: #2196F3;
    border-bottom: 3px solid #2196F3;
    font-weight: 500;
}

QTabBar::tab:hover:!selected {
    background-color: #EEEEEE;
    color: #424242;
}

/* ===== SCROLL BAR ===== */
QScrollBar:vertical {
    background-color: #F5F5F5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #BDBDBD;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #F5F5F5;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #BDBDBD;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== LABEL ===== */
QLabel {
    color: #424242;
}

QLabel[class="heading"] {
    font-size: 20px;
    font-weight: 500;
    color: #212121;
}

QLabel[class="subheading"] {
    font-size: 16px;
    font-weight: 500;
    color: #424242;
}

QLabel[class="caption"] {
    font-size: 12px;
    color: #757575;
}

/* ===== MENU BAR ===== */
QMenuBar {
    background-color: white;
    border-bottom: 1px solid #E0E0E0;
    padding: 4px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #E3F2FD;
}

QMenuBar::item:pressed {
    background-color: #BBDEFB;
}

/* ===== MENU ===== */
QMenu {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QMenu::separator {
    height: 1px;
    background-color: #E0E0E0;
    margin: 4px 8px;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background-color: #E0E0E0;
    border: none;
    border-radius: 4px;
    text-align: center;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #2196F3;
    border-radius: 4px;
}

/* ===== TOOL TIP ===== */
QToolTip {
    background-color: #616161;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
}

/* ===== LIST WIDGET ===== */
QListWidget {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QListWidget::item:hover {
    background-color: #F5F5F5;
}

/* ===== SCROLL AREA ===== */
QScrollArea {
    background-color: white;
    border: none;
}

/* ===== FRAME ===== */
QFrame {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
}

/* ===== MESSAGE BOX ===== */
QMessageBox {
    background-color: white;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


def apply_material_stylesheet(app):
    """
    Apply Material Design Light Theme to the application
    
    Args:
        app: QApplication instance
    """
    app.setStyleSheet(MATERIAL_LIGHT_STYLESHEET)
