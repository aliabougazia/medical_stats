"""
app/styles.py – Application-wide QSS dark theme (Slate/Cyan palette).
"""

COLORS = {
    "bg_dark":      "#0f172a",
    "bg_med":       "#1e293b",
    "bg_light":     "#334155",
    "bg_card":      "#1e293b",
    "accent":       "#0ea5e9",
    "accent2":      "#8b5cf6",
    "accent_hover": "#38bdf8",
    "text":         "#f1f5f9",
    "text_muted":   "#94a3b8",
    "success":      "#22c55e",
    "warning":      "#f59e0b",
    "error":        "#ef4444",
    "border":       "#334155",
    "sidebar":      "#0f172a",
    "sidebar_btn":  "#1e293b",
}

STYLESHEET = """
/* ── Global ──────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: "Segoe UI", "SF Pro Text", Arial, sans-serif;
    font-size: 10pt;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #0f172a;
    border: none;
}

/* ── Labels ──────────────────────────────────── */
QLabel {
    color: #f1f5f9;
    background: transparent;
}
QLabel#section_title {
    font-size: 13pt;
    font-weight: 700;
    color: #f1f5f9;
    padding: 4px 0;
}
QLabel#muted {
    color: #94a3b8;
    font-size: 9pt;
}

/* ── GroupBox ─────────────────────────────────── */
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 10px;
    padding: 8px 10px;
    color: #94a3b8;
    font-size: 9pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #0ea5e9;
}

/* ── Buttons ─────────────────────────────────── */
QPushButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 10pt;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #0ea5e9;
    color: #38bdf8;
}
QPushButton:pressed {
    background-color: #0c4a6e;
    border-color: #0ea5e9;
}
QPushButton:disabled {
    background-color: #1e293b;
    color: #475569;
    border-color: #1e293b;
}
QPushButton#primary {
    background-color: #0ea5e9;
    color: #0f172a;
    font-weight: 700;
    border: none;
}
QPushButton#primary:hover {
    background-color: #38bdf8;
    color: #0f172a;
}
QPushButton#primary:pressed {
    background-color: #0284c7;
}
QPushButton#danger {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #ef4444;
}
QPushButton#danger:hover {
    background-color: #991b1b;
}
QPushButton#success {
    background-color: #14532d;
    color: #86efac;
    border: 1px solid #22c55e;
}
QPushButton#success:hover {
    background-color: #166534;
}

/* ── LineEdit / TextEdit ─────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #0ea5e9;
    selection-color: #0f172a;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #0ea5e9;
}

/* ── ComboBox ─────────────────────────────────── */
QComboBox {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 120px;
}
QComboBox:hover { border-color: #0ea5e9; }
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #94a3b8;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    selection-background-color: #0ea5e9;
    selection-color: #0f172a;
    outline: none;
}

/* ── SpinBox ──────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 8px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #0ea5e9; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #334155;
    border: none;
    width: 18px;
}

/* ── CheckBox / RadioButton ───────────────────── */
QCheckBox, QRadioButton {
    color: #f1f5f9;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 2px solid #334155;
    border-radius: 3px;
    background: #1e293b;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #0ea5e9;
    border-color: #0ea5e9;
}
QRadioButton::indicator { border-radius: 8px; }

/* ── Table ────────────────────────────────────── */
QTableWidget, QTableView {
    background-color: #1e293b;
    color: #f1f5f9;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 6px;
    alternate-background-color: #0f172a;
    selection-background-color: #164e63;
    selection-color: #f1f5f9;
}
QTableWidget::item, QTableView::item {
    padding: 4px 8px;
}
QHeaderView::section {
    background-color: #334155;
    color: #94a3b8;
    font-weight: 600;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #475569;
    border-bottom: 2px solid #0ea5e9;
}

/* ── Scrollbar ────────────────────────────────── */
QScrollBar:vertical {
    background: #1e293b;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #475569;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #0ea5e9; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1e293b;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #475569;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #0ea5e9; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Tabs ─────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 6px;
    background: #1e293b;
}
QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #334155;
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e293b;
    color: #0ea5e9;
    border-bottom: 2px solid #0ea5e9;
}
QTabBar::tab:hover { color: #38bdf8; }

/* ── Splitter ─────────────────────────────────── */
QSplitter::handle {
    background: #334155;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover { background: #0ea5e9; }

/* ── ProgressBar ──────────────────────────────── */
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0ea5e9, stop:1 #8b5cf6);
    border-radius: 4px;
}

/* ── Toolbar (matplotlib) ─────────────────────── */
QToolBar {
    background: #1e293b;
    border: none;
    spacing: 4px;
    padding: 2px;
}
QToolButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
    color: #94a3b8;
}
QToolButton:hover {
    background: #334155;
    color: #0ea5e9;
}

/* ── Status Bar ───────────────────────────────── */
QStatusBar {
    background: #0f172a;
    color: #94a3b8;
    border-top: 1px solid #334155;
    font-size: 9pt;
}

/* ── Sidebar nav buttons ──────────────────────── */
QPushButton#nav_btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 10pt;
}
QPushButton#nav_btn:hover {
    background-color: #1e293b;
    color: #f1f5f9;
}
QPushButton#nav_btn:checked {
    background-color: #1e3a5f;
    color: #38bdf8;
    border-left: 3px solid #0ea5e9;
}

/* ── Frame (card) ─────────────────────────────── */
QFrame#card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
}

/* ── Tooltip ──────────────────────────────────── */
QToolTip {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 4px 8px;
}
"""
