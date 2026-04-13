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
