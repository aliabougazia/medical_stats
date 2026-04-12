"""
app/widgets.py – Reusable Qt widgets: PlotWidget, ResultsTable, ExportBar.
"""
from __future__ import annotations

import io
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QSizePolicy,
    QHeaderView, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
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
