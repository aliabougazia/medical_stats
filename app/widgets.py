"""
app/widgets.py – Reusable Qt widgets: PlotWidget, ResultsTable, ExportBar.
"""
from __future__ import annotations

import io
import logging
import sys
import threading
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QSizePolicy,
    QHeaderView, QLabel, QFrame, QMessageBox, QDialog, QTextEdit,
    QSplitter, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QClipboard, QGuiApplication

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure


# ── Colour constants matching app/styles.py ──────────────────────────────────
_BG_DARK   = "#0f172a"
_BG_MED    = "#1e293b"
_BG_LIGHT  = "#334155"
_ACCENT    = "#0ea5e9"
_ACCENT2   = "#8b5cf6"
_TEXT      = "#f1f5f9"
_MUTED     = "#94a3b8"
_SUCCESS   = "#22c55e"
_WARNING   = "#f59e0b"
_ERROR     = "#ef4444"


# ─────────────────────────────────────────────────────────────────────────────
# safe_run – decorator that catches slot exceptions and shows a dialog
# ─────────────────────────────────────────────────────────────────────────────

import functools
import traceback as _traceback

def safe_run(method):
    """Decorator for panel _run* slots: catches any exception and shows an
    error dialog instead of letting the app crash.
    Qt signals (e.g. clicked(bool)) may pass extra args — they are intentionally
    discarded because none of the decorated slots accept parameters."""
    @functools.wraps(method)
    def wrapper(self, *_qt_args, **_qt_kwargs):
        label = f"{type(self).__name__}.{method.__name__}"
        log_activity(f"▶ Running: {label}", "info")
        try:
            result = method(self)
            log_activity(f"✔ Completed: {label}", "success")
            return result
        except Exception as exc:
            detail = _traceback.format_exc()
            brief  = str(exc) if str(exc) else type(exc).__name__
            log_activity(f"✖ Failed: {label} — {brief}", "error")
            if hasattr(self, "status_message"):
                self.status_message.emit(f"Error: {brief}")
            log_error(brief, detail)
            box = QMessageBox(self)
            box.setWindowTitle("Analysis Error")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(brief)
            box.setDetailedText(detail)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# PlotWidget – embeds a matplotlib Figure with navigation toolbar + save btn
# ─────────────────────────────────────────────────────────────────────────────

class PlotWidget(QWidget):
    """Embeds a matplotlib canvas with dark theme + save button."""

    def __init__(self, parent=None, figsize=(7, 4.5)):
        super().__init__(parent)
        self.figure  = Figure(figsize=figsize, facecolor=_BG_MED)
        self.canvas  = FigureCanvas(self.figure)
        self.canvas.setStyleSheet(f"background:{_BG_MED};")
        self.toolbar = NavToolbar(self.canvas, self)
        self.toolbar.setStyleSheet(f"background:{_BG_MED}; color:{_TEXT};")

        save_btn = QPushButton("💾  Save Plot")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(30)
        save_btn.clicked.connect(self._save)
        copy_btn = QPushButton("📋  Copy")
        copy_btn.setFixedHeight(30)
        copy_btn.clicked.connect(self._copy_to_clipboard)

        btn_row = QHBoxLayout()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)
        layout.addLayout(btn_row)

    # ── axes helpers ─────────────────────────────────────────────────────────

    def get_ax(self, nrows: int = 1, ncols: int = 1):
        """Clear figure and return axes (single ax or list)."""
        self.figure.clear()
        self.figure.patch.set_facecolor(_BG_MED)
        if nrows == 1 and ncols == 1:
            ax = self.figure.add_subplot(111)
            self._style(ax)
            return ax
        axes = []
        for i in range(nrows * ncols):
            ax = self.figure.add_subplot(nrows, ncols, i + 1)
            self._style(ax)
            axes.append(ax)
        return axes

    def _style(self, ax):
        ax.set_facecolor(_BG_DARK)
        ax.tick_params(colors=_MUTED, which="both", labelsize=8)
        ax.xaxis.label.set_color(_TEXT)
        ax.yaxis.label.set_color(_TEXT)
        ax.title.set_color(_TEXT)
        for sp in ax.spines.values():
            sp.set_color(_BG_LIGHT)
        ax.grid(True, color=_BG_LIGHT, linestyle="--", alpha=0.5)

    def draw(self):
        try:
            self.figure.tight_layout()
        except Exception:
            pass
        self.canvas.draw()

    def clear(self):
        self.figure.clear()
        self.canvas.draw()

    # ── save / copy ───────────────────────────────────────────────────────────

    def _save(self):
        path, filt = QFileDialog.getSaveFileName(
            self, "Save Plot", "plot",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;TIFF (*.tif)",
        )
        if path:
            if "." not in path.split("/")[-1]:
                ext = filt.split("*")[1].strip(")")
                path += ext
            self.figure.savefig(path, dpi=300, bbox_inches="tight",
                                 facecolor=self.figure.get_facecolor())

    def _copy_to_clipboard(self):
        buf = io.BytesIO()
        self.figure.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                             facecolor=self.figure.get_facecolor())
        buf.seek(0)
        from PyQt6.QtGui import QImage, QPixmap
        img = QImage.fromData(buf.read())
        QGuiApplication.clipboard().setImage(img)


# ─────────────────────────────────────────────────────────────────────────────
# ResultsTable – displays a pandas DataFrame or list-of-dicts with styling
# ─────────────────────────────────────────────────────────────────────────────

class ResultsTable(QWidget):
    """Styled QTableWidget wrapper with copy/CSV-export buttons."""

    _SIG_COLOR   = QColor("#86efac")   # green for significant
    _NSIG_COLOR  = QColor("#fca5a5")   # red for non-significant p
    _HEAD_COLOR  = QColor(_BG_LIGHT)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        copy_btn = QPushButton("📋  Copy Table")
        copy_btn.setFixedHeight(28)
        copy_btn.clicked.connect(self._copy)
        save_btn = QPushButton("💾  Export CSV")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self._export_csv)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 2, 0, 0)
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._table, stretch=1)
        layout.addLayout(btn_row)

        self._df: pd.DataFrame | None = None

    # ── populate ──────────────────────────────────────────────────────────────

    def show_df(self, df: pd.DataFrame, p_cols: list[str] | None = None):
        """Display a DataFrame; highlight p-value columns."""
        self._df = df.copy()
        self._table.clear()
        self._table.setRowCount(len(df))
        self._table.setColumnCount(len(df.columns))
        self._table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        p_set = set(p_cols or [c for c in df.columns if str(c).lower() in ("p", "p-value", "p_value", "pvalue")])

        for r, (_, row) in enumerate(df.iterrows()):
            for c, val in enumerate(row):
                col_name = str(df.columns[c])
                txt = self._fmt(val, col_name in p_set)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Colour coding for p-values
                if col_name in p_set:
                    try:
                        pnum = float(val)
                        if pnum < 0.05:
                            item.setForeground(self._SIG_COLOR)
                            f = item.font(); f.setBold(True); item.setFont(f)
                        else:
                            item.setForeground(self._NSIG_COLOR)
                    except (TypeError, ValueError):
                        pass
                self._table.setItem(r, c, item)
        self._table.resizeColumnsToContents()

    def show_dict(self, d: dict):
        """Display key-value dict as a two-column table."""
        rows = [(k, v) for k, v in d.items() if not isinstance(v, (pd.DataFrame, np.ndarray, list))]
        df   = pd.DataFrame(rows, columns=["Metric", "Value"])
        self.show_df(df)

    @staticmethod
    def _fmt(val, is_p: bool = False) -> str:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        if is_p:
            try:
                pv = float(val)
                if pv < 0.001:
                    return "<0.001 ***"
                if pv < 0.01:
                    return f"{pv:.4f} **"
                if pv < 0.05:
                    return f"{pv:.4f} *"
                return f"{pv:.4f}"
            except (TypeError, ValueError):
                pass
        if isinstance(val, float):
            return f"{val:.4g}"
        if isinstance(val, bool):
            return "Yes" if val else "No"
        return str(val)

    # ── export ────────────────────────────────────────────────────────────────

    def _copy(self):
        if self._df is None:
            return
        QGuiApplication.clipboard().setText(self._df.to_csv(index=False, sep="\t"))

    def _export_csv(self):
        if self._df is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "results.csv", "CSV (*.csv)")
        if path:
            self._df.to_csv(path, index=False)


# ─────────────────────────────────────────────────────────────────────────────
# SectionHeader
# ─────────────────────────────────────────────────────────────────────────────

class SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("section_title")
        self.setStyleSheet(
            f"color:{_TEXT}; font-size:14pt; font-weight:700;"
            f" padding:8px 0 4px 0; background:transparent;"
        )


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"color:{_BG_LIGHT}; background:{_BG_LIGHT};")
        self.setFixedHeight(1)


# ─────────────────────────────────────────────────────────────────────────────
# StatusBadge
# ─────────────────────────────────────────────────────────────────────────────

class StatusBadge(QLabel):
    """Small coloured pill indicating significance / connected status."""

    def __init__(self, text: str = "", color: str = _ACCENT, parent=None):
        super().__init__(text, parent)
        self._set_color(color)

    def set_ok(self, msg: str = "Connected"):
        self._set_color(_SUCCESS); self.setText(f"  ●  {msg}  ")

    def set_error(self, msg: str = "Error"):
        self._set_color(_ERROR); self.setText(f"  ●  {msg}  ")

    def set_neutral(self, msg: str = ""):
        self._set_color(_MUTED); self.setText(f"  ●  {msg}  " if msg else "")

    def _set_color(self, c: str):
        self.setStyleSheet(
            f"background:{c}22; color:{c}; border:1px solid {c}; "
            f"border-radius:10px; padding:2px 8px; font-size:8pt; font-weight:600;"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DebugWindow – persistent, re-openable activity + error log
# ─────────────────────────────────────────────────────────────────────────────

_MONO_FONT = QFont("Consolas, Fira Mono, Courier New, monospace", 9)

# Colour tags for HTML activity log
_TAG_INFO    = _TEXT
_TAG_SUCCESS = _SUCCESS
_TAG_WARNING = _WARNING
_TAG_ERROR   = _ERROR
_TAG_STDOUT  = "#bae6fd"   # light blue
_TAG_STDERR  = "#fca5a5"   # light red
_TAG_LOG     = "#d8b4fe"   # light purple


class _ActivitySignals(QObject):
    """Carry log messages across threads safely into the Qt main thread."""
    message = pyqtSignal(str, str)   # (html_line, level)


class DebugWindow(QDialog):
    """Non-modal window showing a live Activity Log and an Error Log."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("MedStat Pro – Debug Console")
        self.resize(980, 620)
        self.setStyleSheet(
            f"QDialog {{ background:{_BG_DARK}; color:{_TEXT}; }}"
            f"QTextEdit {{ background:{_BG_MED}; color:{_TEXT}; border:1px solid {_BG_LIGHT};"
            f"  border-radius:4px; padding:6px; }}"
            f"QPushButton {{ background:{_BG_LIGHT}; color:{_TEXT}; border:none;"
            f"  border-radius:4px; padding:5px 14px; font-size:9pt; }}"
            f"QPushButton:hover {{ background:{_ACCENT}; color:#fff; }}"
            f"QLabel {{ color:{_MUTED}; font-size:9pt; background:transparent; }}"
            f"QTabWidget::pane {{ border:1px solid {_BG_LIGHT}; border-radius:4px; }}"
            f"QTabBar::tab {{ background:{_BG_LIGHT}; color:{_MUTED}; padding:6px 18px;"
            f"  border-radius:4px 4px 0 0; margin-right:2px; font-size:9pt; }}"
            f"QTabBar::tab:selected {{ background:{_ACCENT}; color:#fff; font-weight:600; }}"
        )
        self._error_entries: list[str] = []
        self._signals = _ActivitySignals()
        self._signals.message.connect(self._append_activity_html)
        self._activity_line_count = 0
        self._MAX_ACTIVITY_LINES = 2000
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # ── header row ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Debug Console")
        title.setStyleSheet(f"color:{_TEXT}; font-size:11pt; font-weight:700;")
        hdr.addWidget(title)
        hdr.addStretch()

        self._error_count_lbl = QLabel("No errors")
        hdr.addWidget(self._error_count_lbl)

        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        # ── tabs ──────────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        root.addWidget(self._tabs, stretch=1)

        # ── Tab 1: Activity Log ───────────────────────────────────────────────
        activity_widget = QWidget()
        av = QVBoxLayout(activity_widget)
        av.setContentsMargins(0, 6, 0, 0)
        av.setSpacing(4)

        act_btns = QHBoxLayout()
        act_copy = QPushButton("📋  Copy")
        act_copy.setFixedHeight(28)
        act_copy.clicked.connect(self._copy_activity)
        act_clear = QPushButton("🗑  Clear")
        act_clear.setFixedHeight(28)
        act_clear.clicked.connect(self._clear_activity)

        self._wrap_chk = QPushButton("↔  Wrap")
        self._wrap_chk.setFixedHeight(28)
        self._wrap_chk.setCheckable(True)
        self._wrap_chk.toggled.connect(self._toggle_wrap)

        act_btns.addWidget(act_copy)
        act_btns.addWidget(act_clear)
        act_btns.addWidget(self._wrap_chk)
        act_btns.addStretch()

        legend = QLabel(
            f"<span style='color:{_TAG_INFO}'>■ info</span>  "
            f"<span style='color:{_TAG_SUCCESS}'>■ ok</span>  "
            f"<span style='color:{_TAG_STDOUT}'>■ stdout</span>  "
            f"<span style='color:{_TAG_STDERR}'>■ stderr</span>  "
            f"<span style='color:{_TAG_LOG}'>■ logging</span>  "
            f"<span style='color:{_TAG_ERROR}'>■ error</span>"
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        act_btns.addWidget(legend)
        av.addLayout(act_btns)

        self._activity_text = QTextEdit()
        self._activity_text.setReadOnly(True)
        self._activity_text.setFont(_MONO_FONT)
        self._activity_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._activity_text.setPlaceholderText(
            "Activity will appear here as you use the application.\n"
            "stdout, stderr, logging output and analysis events are captured automatically."
        )
        av.addWidget(self._activity_text, stretch=1)
        self._tabs.addTab(activity_widget, "📋  Activity Log")

        # ── Tab 2: Error Log ──────────────────────────────────────────────────
        error_widget = QWidget()
        ev = QVBoxLayout(error_widget)
        ev.setContentsMargins(0, 6, 0, 0)
        ev.setSpacing(4)

        err_btns = QHBoxLayout()
        err_copy = QPushButton("📋  Copy All")
        err_copy.setFixedHeight(28)
        err_copy.clicked.connect(self._copy_errors)
        err_clear = QPushButton("🗑  Clear")
        err_clear.setFixedHeight(28)
        err_clear.clicked.connect(self._clear_errors)
        err_btns.addWidget(err_copy)
        err_btns.addWidget(err_clear)
        err_btns.addStretch()
        ev.addLayout(err_btns)

        self._error_text = QTextEdit()
        self._error_text.setReadOnly(True)
        self._error_text.setFont(_MONO_FONT)
        self._error_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._error_text.setPlaceholderText(
            "No errors have been captured yet.\n\n"
            "Errors from all panels are recorded here automatically."
        )
        ev.addWidget(self._error_text, stretch=1)

        note = QLabel(
            "Errors are captured automatically whenever an analysis fails. "
            "Use 'Copy All' to share the log for support."
        )
        note.setWordWrap(True)
        ev.addWidget(note)
        self._tabs.addTab(error_widget, "🔴  Errors")

    # ── public API ────────────────────────────────────────────────────────────

    def log(self, brief: str, detail: str) -> None:
        """Append an error entry (error tab)."""
        ts = QDateTime.currentDateTime().toString("yyyy-MM-dd  HH:mm:ss")
        separator = "─" * 72
        entry = f"[{ts}]  {brief}\n{separator}\n{detail.rstrip()}\n"
        self._error_entries.append(entry)
        self._error_text.setPlainText("\n".join(self._error_entries))
        sb = self._error_text.verticalScrollBar()
        sb.setValue(sb.maximum())
        n = len(self._error_entries)
        self._error_count_lbl.setText(f"{n} error{'s' if n != 1 else ''} logged")
        self._error_count_lbl.setStyleSheet(f"color:{_ERROR}; font-size:9pt; font-weight:600;")
        # Switch to error tab so user notices
        self._tabs.setCurrentIndex(1)
        # Also post to activity log
        self.activity(f"[ERROR] {brief}", "error")

    def activity(self, message: str, level: str = "info") -> None:
        """Thread-safe: emit a line to the Activity Log tab."""
        ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
        colour = {
            "info": _TAG_INFO, "success": _TAG_SUCCESS, "warning": _TAG_WARNING,
            "error": _TAG_ERROR, "stdout": _TAG_STDOUT, "stderr": _TAG_STDERR,
            "log": _TAG_LOG,
        }.get(level, _TAG_INFO)
        # Escape HTML special chars
        safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = (
            f"<span style='color:{_MUTED}'>{ts}</span> "
            f"<span style='color:{colour}'>{safe_msg}</span>"
        )
        self._signals.message.emit(html, level)

    def error_count(self) -> int:
        return len(self._error_entries)

    # ── private slots ─────────────────────────────────────────────────────────

    def _append_activity_html(self, html: str, level: str) -> None:
        """Called on main thread via signal."""
        # Trim if too many lines
        if self._activity_line_count >= self._MAX_ACTIVITY_LINES:
            cursor = self._activity_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down,
                                cursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            self._activity_line_count = max(0, self._activity_line_count - 100)
        self._activity_text.append(html)
        self._activity_line_count += 1
        sb = self._activity_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_activity(self):
        QGuiApplication.clipboard().setText(self._activity_text.toPlainText())

    def _clear_activity(self):
        self._activity_text.clear()
        self._activity_line_count = 0

    def _toggle_wrap(self, checked: bool):
        mode = QTextEdit.LineWrapMode.WidgetWidth if checked else QTextEdit.LineWrapMode.NoWrap
        self._activity_text.setLineWrapMode(mode)

    def _copy_errors(self):
        QGuiApplication.clipboard().setText(self._error_text.toPlainText())

    def _clear_errors(self):
        self._error_entries.clear()
        self._error_text.clear()
        self._error_count_lbl.setText("No errors")
        self._error_count_lbl.setStyleSheet(f"color:{_MUTED}; font-size:9pt;")
        self._tabs.setTabText(1, "🔴  Errors")


# ── module-level singleton ────────────────────────────────────────────────────

_debug_window_instance: DebugWindow | None = None
_redirects_installed = False


class _StdoutRedirect(io.TextIOBase):
    """Writes to original stdout AND to the Activity Log."""
    def __init__(self, original):
        self._orig = original

    def write(self, text: str) -> int:
        if self._orig:
            self._orig.write(text)
        if text.strip():
            get_debug_window().activity(text.rstrip(), "stdout")
        return len(text)

    def flush(self):
        if self._orig:
            self._orig.flush()


class _StderrRedirect(io.TextIOBase):
    """Writes to original stderr AND to the Activity Log."""
    def __init__(self, original):
        self._orig = original

    def write(self, text: str) -> int:
        if self._orig:
            self._orig.write(text)
        if text.strip():
            get_debug_window().activity(text.rstrip(), "stderr")
        return len(text)

    def flush(self):
        if self._orig:
            self._orig.flush()


class _QtLogHandler(logging.Handler):
    """Routes Python logging records to the Activity Log."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            level = {
                logging.DEBUG: "log",
                logging.INFO: "log",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "error",
            }.get(record.levelno, "log")
            get_debug_window().activity(f"[{record.levelname}] {msg}", level)
        except Exception:
            pass


def _install_redirects() -> None:
    """Install stdout/stderr redirects and logging handler once."""
    global _redirects_installed
    if _redirects_installed:
        return
    _redirects_installed = True
    sys.stdout = _StdoutRedirect(sys.__stdout__)
    sys.stderr = _StderrRedirect(sys.__stderr__)
    handler = _QtLogHandler()
    handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
    # Ensure root logger passes everything through
    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET or root_logger.level > logging.DEBUG:
        root_logger.setLevel(logging.DEBUG)


def get_debug_window() -> DebugWindow:
    """Return the application-wide DebugWindow, creating it on first call."""
    global _debug_window_instance
    if _debug_window_instance is None:
        _debug_window_instance = DebugWindow()
        _install_redirects()
    return _debug_window_instance


def log_error(brief: str, detail: str) -> None:
    """Append an error entry to the debug window."""
    get_debug_window().log(brief, detail)


def log_activity(message: str, level: str = "info") -> None:
    """Append an activity message to the debug window activity log."""
    get_debug_window().activity(message, level)


# ─────────────────────────────────────────────────────────────────────────────
# DataHighlightWindow – shows which cells/columns/rows are used in a test
# ─────────────────────────────────────────────────────────────────────────────

_MAX_HIGHLIGHT_ROWS = 500

# Role → header foreground colour and cell background colour
_ROLE_HDR_FG = {
    "outcome": "#38bdf8",   # sky blue
    "group":   "#c084fc",   # purple
    "factor":  "#4ade80",   # green
    "extra":   "#fbbf24",   # amber
}
_ROLE_CELL_BG = {
    "outcome": "#0c2d48",
    "group":   "#1e0f3d",
    "factor":  "#0f2d1a",
    "extra":   "#2d1f04",
}
# Per-group-value cell background + foreground (cycles)
_GRP_CELL_BG = ["#1a2e4a", "#2a1a4a", "#0f2d1a", "#2d200a", "#2d0a0a", "#042d2d",
                "#1a1a2e", "#2d1a0f", "#0a2d2d", "#2a0a1a"]
_GRP_CELL_FG = ["#38bdf8", "#c084fc", "#4ade80", "#fbbf24", "#f87171", "#22d3ee",
                "#a78bfa", "#fb923c", "#34d399", "#f472b6"]


def _to_str_list(v) -> list[str]:
    """Normalise a context value to a flat list of non-empty strings."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    return [x for x in v if x]


class DataHighlightWindow(QDialog):
    """Non-modal window displaying the DataFrame with colour-coded roles.

    Call ``show_highlight(df, context)`` to update it.

    ``context`` keys (all optional):
        test_name   str          – shown in title
        outcome     str|list     – outcome / dependent variable column(s)
        group       str          – group column
        keep_groups list[str]    – subset of group values actually used
        factors     list[str]    – factor columns (ANOVA etc.)
        extra       list[str]    – other used columns
    """

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("MedStat Pro – Data Inspector")
        self.resize(1100, 680)
        self.setStyleSheet(
            f"QDialog {{ background:{_BG_DARK}; color:{_TEXT}; }}"
            f"QTableWidget {{ background:{_BG_MED}; color:{_TEXT};"
            f"  gridline-color:{_BG_LIGHT}; border:1px solid {_BG_LIGHT};"
            f"  border-radius:4px; font-size:8pt; }}"
            f"QHeaderView::section {{ background:{_BG_LIGHT}; color:{_TEXT};"
            f"  padding:3px 6px; border:none; border-right:1px solid {_BG_DARK};"
            f"  font-size:8pt; }}"
            f"QPushButton {{ background:{_BG_LIGHT}; color:{_TEXT}; border:none;"
            f"  border-radius:4px; padding:5px 14px; font-size:9pt; }}"
            f"QPushButton:hover {{ background:{_ACCENT}; color:#fff; }}"
            f"QLabel {{ color:{_MUTED}; font-size:9pt; background:transparent; }}"
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # ── header row ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        self._title_lbl = QLabel("Data Inspector")
        self._title_lbl.setStyleSheet(
            f"color:{_TEXT}; font-size:11pt; font-weight:700;")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()
        self._info_lbl = QLabel("")
        hdr.addWidget(self._info_lbl)
        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        # ── legend ────────────────────────────────────────────────────────────
        self._legend_lbl = QLabel("")
        self._legend_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._legend_lbl.setWordWrap(True)
        root.addWidget(self._legend_lbl)

        # ── table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setDefaultSectionSize(110)
        self._table.verticalHeader().setDefaultSectionSize(22)
        self._table.setAlternatingRowColors(False)
        root.addWidget(self._table, stretch=1)

    # ── public API ────────────────────────────────────────────────────────────

    def show_highlight(self, df: "pd.DataFrame | None", context: dict) -> None:
        """Populate / refresh the table according to *context*."""
        test_name = context.get("test_name", "")
        self._title_lbl.setText(
            f"Data Inspector  —  {test_name}" if test_name else "Data Inspector")

        if df is None or df.empty:
            self._table.clear()
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            self._legend_lbl.setText("<i>No data loaded.</i>")
            self._info_lbl.setText("")
            return

        outcome_cols = _to_str_list(context.get("outcome"))
        group_col    = context.get("group") or ""
        keep_groups  = context.get("keep_groups")    # None = all groups
        factor_cols  = _to_str_list(context.get("factors"))
        extra_cols   = _to_str_list(context.get("extra"))

        all_cols = list(df.columns)

        # ── which rows are "included" ─────────────────────────────────────────
        if group_col and group_col in df.columns and keep_groups is not None:
            norm = df[group_col].astype(str).str.strip()
            included_mask = norm.isin(keep_groups).values
        else:
            included_mask = None   # all rows included

        # ── group-value → palette index ───────────────────────────────────────
        group_val_idx: dict[str, int] = {}
        if group_col and group_col in df.columns:
            vals = sorted(
                df[group_col].dropna().astype(str).str.strip().unique())
            group_val_idx = {v: i for i, v in enumerate(vals)}

        # ── col role map ──────────────────────────────────────────────────────
        col_role: dict[str, str] = {}
        for c in outcome_cols:
            if c in all_cols:
                col_role[c] = "outcome"
        if group_col in all_cols:
            col_role[group_col] = "group"
        for c in factor_cols:
            if c in all_cols:
                col_role[c] = "factor"
        for c in extra_cols:
            if c in all_cols:
                col_role.setdefault(c, "extra")

        # ── truncate ──────────────────────────────────────────────────────────
        display_df = df.iloc[:_MAX_HIGHLIGHT_ROWS]
        truncated  = len(df) > _MAX_HIGHLIGHT_ROWS
        n_included = int(included_mask.sum()) if included_mask is not None else len(df)
        info = (f"Showing first {_MAX_HIGHLIGHT_ROWS} of {len(df)} rows" if truncated
                else f"{len(df)} rows")
        if included_mask is not None and n_included < len(df):
            info += f"  |  {n_included} included  ·  {len(df)-n_included} excluded (dimmed)"
        self._info_lbl.setText(info)

        # ── populate table ────────────────────────────────────────────────────
        nc = len(all_cols)
        nr = len(display_df)
        self._table.setUpdatesEnabled(False)
        self._table.clearContents()
        self._table.setColumnCount(nc)
        self._table.setRowCount(nr)

        # Column headers – bold + coloured foreground for used cols
        for ci, col in enumerate(all_cols):
            role = col_role.get(col)
            label = col
            if role:
                label = f"▸ {col}"
            item = QTableWidgetItem(label)
            if role:
                fg = _ROLE_HDR_FG.get(role, _TEXT)
                item.setForeground(QColor(fg))
                item.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            else:
                item.setForeground(QColor(_MUTED))
            self._table.setHorizontalHeaderItem(ci, item)

        # Cells
        norm_grp = (df[group_col].astype(str).str.strip()
                    if group_col and group_col in df.columns else None)

        for ri in range(nr):
            row = display_df.iloc[ri]
            row_included = (bool(included_mask[ri])
                            if included_mask is not None else True)
            grp_val = norm_grp.iloc[ri] if norm_grp is not None else None

            for ci, col in enumerate(all_cols):
                val  = row[col]
                text = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if not row_included:
                    # Dim excluded rows
                    item.setForeground(QColor("#3d4f63"))
                    item.setBackground(QColor("#111827"))
                elif col == group_col and grp_val is not None:
                    idx_g = group_val_idx.get(grp_val, 0)
                    item.setBackground(
                        QColor(_GRP_CELL_BG[idx_g % len(_GRP_CELL_BG)]))
                    item.setForeground(
                        QColor(_GRP_CELL_FG[idx_g % len(_GRP_CELL_FG)]))
                elif col in col_role:
                    role = col_role[col]
                    item.setBackground(
                        QColor(_ROLE_CELL_BG.get(role, _BG_MED)))
                    item.setForeground(QColor("#e2e8f0"))
                else:
                    item.setBackground(QColor(_BG_MED))
                    item.setForeground(QColor("#475569"))

                self._table.setItem(ri, ci, item)

        self._table.setUpdatesEnabled(True)

        # ── legend ────────────────────────────────────────────────────────────
        parts = []

        def _badge(color: str, text: str) -> str:
            return (f"<span style='background:{color}33; color:{color};"
                    f" border:1px solid {color}55;"
                    f" padding:1px 7px; border-radius:3px;'>{text}</span>")

        if outcome_cols:
            parts.append(_badge(_ROLE_HDR_FG["outcome"],
                                 "Outcome: " + ", ".join(outcome_cols)))
        if group_col:
            parts.append(_badge(_ROLE_HDR_FG["group"], f"Group: {group_col}"))
            # Per-value sub-badges
            for gv, gi in sorted(group_val_idx.items(), key=lambda x: x[1]):
                fg = _GRP_CELL_FG[gi % len(_GRP_CELL_FG)]
                excluded = keep_groups is not None and gv not in keep_groups
                style = (f"background:{_GRP_CELL_BG[gi%len(_GRP_CELL_BG)]};"
                         f" color:{fg}; padding:1px 5px; border-radius:3px;"
                         + (" text-decoration:line-through; opacity:0.5;" if excluded else ""))
                parts.append(f"<span style='{style}'>{gv}"
                              + ("  ✗" if excluded else "") + "</span>")
        for i, fc in enumerate(factor_cols):
            parts.append(_badge(_ROLE_HDR_FG["factor"], f"Factor: {fc}"))
        if extra_cols:
            parts.append(_badge(_ROLE_HDR_FG["extra"],
                                 "Used: " + ", ".join(extra_cols)))
        parts.append(f"<span style='color:#475569;'>◻ Unused</span>")
        if included_mask is not None and not all(included_mask):
            parts.append(f"<span style='color:#3d4f63;'>◻ Excluded rows (dimmed)</span>")

        self._legend_lbl.setText("  &nbsp;  ".join(parts))


# ── module-level singleton ────────────────────────────────────────────────────

_data_highlight_window_instance: DataHighlightWindow | None = None


def get_data_highlight_window() -> DataHighlightWindow:
    """Return the application-wide DataHighlightWindow, creating it on first call."""
    global _data_highlight_window_instance
    if _data_highlight_window_instance is None:
        _data_highlight_window_instance = DataHighlightWindow()
    return _data_highlight_window_instance
