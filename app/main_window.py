"""
app/main_window.py – Main application window with sidebar navigation.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QStatusBar,
    QFrame, QScrollArea, QSizePolicy, QFileDialog,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon

from .styles import STYLESHEET
from .core import data_store
from .widgets import get_debug_window

# ── Lazy panel imports to keep startup fast ────────────────────────────────

def _import_panels():
    from .panel_data        import DataPanel
    from .panel_descriptive import DescriptivePanel
    from .panel_diagnostic  import DiagnosticPanel
    from .panel_tests       import TestsPanel
    from .panel_regression  import RegressionPanel
    from .panel_reliability import ReliabilityPanel
    from .panel_correlation import CorrelationPanel
    from .panel_survival    import SurvivalPanel
    from .panel_ai          import AIAssistantPanel
    return (DataPanel, DescriptivePanel, DiagnosticPanel, TestsPanel,
            RegressionPanel, ReliabilityPanel, CorrelationPanel,
            SurvivalPanel, AIAssistantPanel)


# ── Nav item definitions ──────────────────────────────────────────────────────

_NAV_ITEMS = [
    ("🗃",  "Data Manager"),
    ("📊",  "Descriptive Stats"),
    ("🩺",  "Diagnostic Tests"),
    ("📐",  "Statistical Tests"),
    ("📈",  "Regression"),
    ("🔁",  "Reliability"),
    ("🔗",  "Correlation"),
    ("⏱",  "Survival Analysis"),
    ("🤖",  "AI Assistant"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MedStat Pro  –  Advanced Medical Research Statistics")
        self.setMinimumSize(1100, 720)
        self.resize(1360, 820)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_statusbars()
        data_store.add_listener(self._update_data_badge)

    # ── Main layout ───────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = self._build_sidebar()
        main_lay.addWidget(sidebar)

        # ── Content area ──────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_lay.addWidget(self._stack, stretch=1)

        # Lazy-load all panels
        (DataPanel, DescriptivePanel, DiagnosticPanel, TestsPanel,
         RegressionPanel, ReliabilityPanel, CorrelationPanel,
         SurvivalPanel, AIAssistantPanel) = _import_panels()

        self._panels = [
            DataPanel(),
            DescriptivePanel(),
            DiagnosticPanel(),
            TestsPanel(),
            RegressionPanel(),
            ReliabilityPanel(),
            CorrelationPanel(),
            SurvivalPanel(),
            AIAssistantPanel(),
        ]
        for panel in self._panels:
            self._stack.addWidget(panel)

        # Status bar
        self._status = QStatusBar()
        self._status.setObjectName("statusbar")
        self._data_badge = QLabel("  No data  ")
        self._data_badge.setStyleSheet(
            "color:#94a3b8; font-size:9pt; padding:0 8px;"
        )
        self._status.addPermanentWidget(self._data_badge)
        self.setStatusBar(self._status)
        self._status.showMessage("Welcome to MedStat Pro. Load or paste data to begin.")

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setFixedWidth(220)
        sb.setStyleSheet(
            "background:#0b1120; border-right: 1px solid #1e293b;"
        )
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        # Logo / app name
        logo_lbl = QLabel("MedStat Pro")
        logo_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color:#0ea5e9; padding:6px 8px 14px 6px;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(logo_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#1e293b;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        layout.addSpacing(6)

        # Nav buttons
        self._nav_buttons: list[QPushButton] = []
        for icon, label in _NAV_ITEMS:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._make_nav_handler(len(self._nav_buttons)))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Bottom: debug log button
        debug_btn = QPushButton("  🐛   Debug Log")
        debug_btn.setObjectName("nav_btn")
        debug_btn.setMinimumHeight(36)
        debug_btn.setFont(QFont("Segoe UI", 10))
        debug_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        debug_btn.setStyleSheet(
            "QPushButton { color:#94a3b8; } "
            "QPushButton:hover { color:#ef4444; background:#1e293b; border-left:3px solid #ef4444; }"
        )
        debug_btn.clicked.connect(self._open_debug_window)
        layout.addWidget(debug_btn)

        # Bottom: version
        ver_lbl = QLabel("v1.0.0  |  2026")
        ver_lbl.setStyleSheet("color:#334155; font-size:8pt; padding:4px 8px;")
        layout.addWidget(ver_lbl)

        # Select first
        self._nav_buttons[0].setChecked(True)
        return sb

    def _make_nav_handler(self, idx: int):
        def handler():
            self._stack.setCurrentIndex(idx)
            for i, btn in enumerate(self._nav_buttons):
                btn.setChecked(i == idx)
        return handler

    # ── Status helpers ────────────────────────────────────────────────────────

    def _connect_statusbars(self):
        for panel in self._panels:
            sig = getattr(panel, "status_message", None)
            if sig is not None:
                sig.connect(self._status.showMessage)

    def _open_debug_window(self):
        win = get_debug_window()
        win.show()
        win.raise_()
        win.activateWindow()

    def _update_data_badge(self):
        df = data_store.df
        if df is None:
            self._data_badge.setText("  No data  ")
            self._data_badge.setStyleSheet("color:#94a3b8; font-size:9pt; padding:0 8px;")
        else:
            self._data_badge.setText(
                f"  📊  {len(df)} rows × {len(df.columns)} cols  "
                f"| {data_store.filename}  "
            )
            self._data_badge.setStyleSheet("color:#22c55e; font-size:9pt; padding:0 8px;")
