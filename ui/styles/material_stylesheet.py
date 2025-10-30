# -*- coding: utf-8 -*-
"""
Material Design Stylesheet for PyQt5 Application
Modern, clean design with Material Design principles
"""

MATERIAL_STYLESHEET = """
/* Global */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Buttons */
QPushButton {
    background: #2196F3;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background: #64B5F6;
}

QPushButton:pressed {
    background: #1976D2;
}

QPushButton:disabled {
    background: #BDBDBD;
    color: #757575;
}

/* Secondary Buttons */
QPushButton[class="secondary"] {
    background: #757575;
}

QPushButton[class="secondary"]:hover {
    background: #9E9E9E;
}

/* Success Buttons */
QPushButton[class="success"] {
    background: #4CAF50;
}

QPushButton[class="success"]:hover {
    background: #66BB6A;
}

/* Warning Buttons */
QPushButton[class="warning"] {
    background: #FF9800;
}

QPushButton[class="warning"]:hover {
    background: #FFB74D;
}

/* Danger Buttons */
QPushButton[class="danger"] {
    background: #F44336;
}

QPushButton[class="danger"]:hover {
    background: #EF5350;
}

/* Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 12px;
    color: #212121;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #2196F3;
    padding: 11px;
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    background: #F5F5F5;
    color: #9E9E9E;
}

/* Combo Box */
QComboBox {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 10px;
    min-width: 100px;
}

QComboBox:hover {
    border: 1px solid #2196F3;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox::down-arrow {
    image: none;
    border: none;
}

QComboBox QAbstractItemView {
    background: white;
    border: 1px solid #E0E0E0;
    selection-background-color: #E3F2FD;
    selection-color: #212121;
}

/* Spin Box */
QSpinBox {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 10px;
}

QSpinBox:focus {
    border: 2px solid #2196F3;
    padding: 9px;
}

/* List Widget */
QListWidget {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #F5F5F5;
}

QListWidget::item:selected {
    background: #E3F2FD;
    color: #212121;
}

QListWidget::item:hover {
    background: #F5F5F5;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    background: white;
}

QTabBar::tab {
    background: #F5F5F5;
    border: 1px solid #E0E0E0;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: white;
    border-bottom: 3px solid #2196F3;
}

QTabBar::tab:hover {
    background: #E0E0E0;
}

/* Group Box */
QGroupBox {
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    background: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 5px 10px;
    color: #424242;
    font-weight: 600;
}

/* Scroll Bar */
QScrollBar:vertical {
    border: none;
    background: #F5F5F5;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    border: none;
    background: #F5F5F5;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #BDBDBD;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Labels */
QLabel {
    color: #424242;
}

QLabel[class="title"] {
    font-size: 24px;
    font-weight: 600;
    color: #212121;
}

QLabel[class="subtitle"] {
    font-size: 18px;
    font-weight: 500;
    color: #424242;
}

QLabel[class="caption"] {
    font-size: 11px;
    color: #757575;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    text-align: center;
    background: #F5F5F5;
}

QProgressBar::chunk {
    background: #2196F3;
    border-radius: 3px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #757575;
    border-radius: 3px;
    background: white;
}

QCheckBox::indicator:checked {
    background: #2196F3;
    border: 2px solid #2196F3;
}

QCheckBox::indicator:hover {
    border: 2px solid #2196F3;
}

/* Radio Button */
QRadioButton {
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #757575;
    border-radius: 9px;
    background: white;
}

QRadioButton::indicator:checked {
    background: #2196F3;
    border: 2px solid #2196F3;
}

QRadioButton::indicator:hover {
    border: 2px solid #2196F3;
}

/* Menu Bar */
QMenuBar {
    background: white;
    border-bottom: 1px solid #E0E0E0;
}

QMenuBar::item {
    padding: 8px 12px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #E3F2FD;
}

QMenu {
    background: white;
    border: 1px solid #E0E0E0;
}

QMenu::item {
    padding: 8px 24px;
}

QMenu::item:selected {
    background: #E3F2FD;
}

/* Tool Button */
QToolButton {
    background: transparent;
    border: none;
    padding: 8px;
    border-radius: 4px;
}

QToolButton:hover {
    background: #F5F5F5;
}

QToolButton:pressed {
    background: #E0E0E0;
}
"""


def apply_material_design(app):
    """
    Apply Material Design stylesheet to the application
    
    Args:
        app: QApplication instance
    """
    app.setStyleSheet(MATERIAL_STYLESHEET)
