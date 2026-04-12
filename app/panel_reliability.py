"""
app/panel_reliability.py – Intra/Inter-observer Variability panel.

Includes:
 • Cohen's Kappa  (categorical)
 • Weighted Kappa (ordinal)
 • Intraclass Correlation Coefficient – ICC (continuous)
 • Bland-Altman analysis + plot
 • Cronbach's Alpha
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QListWidget, QAbstractItemView, QGroupBox,
    QSplitter, QTabWidget, QScrollArea, QFormLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .core import data_store
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider
from . import statistics as S


class ReliabilityPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Reliability & Agreement"))
        root.addWidget(Divider())

        tabs = QTabWidget()

        t1 = QWidget(); self._build_kappa_tab(t1)
        tabs.addTab(t1, "  Cohen's Kappa  ")

        t2 = QWidget(); self._build_icc_tab(t2)
        tabs.addTab(t2, "  ICC  ")

        t3 = QWidget(); self._build_ba_tab(t3)
        tabs.addTab(t3, "  Bland-Altman  ")

        t4 = QWidget(); self._build_alpha_tab(t4)
        tabs.addTab(t4, "  Cronbach's α  ")

        root.addWidget(tabs, stretch=1)

    # ── Kappa tab ─────────────────────────────────────────────────────────────

    def _build_kappa_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)
        grp  = QGroupBox("Configuration")
        gl   = QFormLayout(grp)
        self._kappa_r1 = QComboBox(); gl.addRow("Rater 1:", self._kappa_r1)
        self._kappa_r2 = QComboBox(); gl.addRow("Rater 2:", self._kappa_r2)
        llay.addWidget(grp)
        btn = QPushButton("▶  Calculate Kappa"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_kappa)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        self._kappa_table = ResultsTable()
        self._kappa_plot  = PlotWidget(figsize=(5, 4))
        rlay.addWidget(self._kappa_table, stretch=1); rlay.addWidget(self._kappa_plot, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── ICC tab ───────────────────────────────────────────────────────────────

    def _build_icc_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)
        grp  = QGroupBox("Select Rater Columns (Ctrl+click ≥2)")
        gl   = QVBoxLayout(grp)
        self._icc_list = QListWidget()
        self._icc_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._icc_list.setMaximumHeight(180)
        gl.addWidget(self._icc_list)
        llay.addWidget(grp)
        btn = QPushButton("▶  Calculate ICC"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_icc)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        self._icc_table = ResultsTable()
        self._icc_plot  = PlotWidget(figsize=(5, 4))
        rlay.addWidget(self._icc_table, stretch=2); rlay.addWidget(self._icc_plot, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Bland-Altman tab ──────────────────────────────────────────────────────

    def _build_ba_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)
        grp  = QGroupBox("Configuration")
        gl   = QFormLayout(grp)
        self._ba_m1 = QComboBox(); gl.addRow("Method 1:", self._ba_m1)
        self._ba_m2 = QComboBox(); gl.addRow("Method 2:", self._ba_m2)
        llay.addWidget(grp)
        btn = QPushButton("▶  Bland-Altman Analysis"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_ba)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        rtabs = QTabWidget()
        self._ba_table = ResultsTable()
        self._ba_plot  = PlotWidget(figsize=(7, 5))
        rtabs.addTab(self._ba_table,  "📋  Statistics")
        rtabs.addTab(self._ba_plot,   "📊  Bland-Altman Plot")
        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Cronbach tab ──────────────────────────────────────────────────────────

    def _build_alpha_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)
        grp  = QGroupBox("Select Item Columns (Ctrl+click ≥2)")
        gl   = QVBoxLayout(grp)
        self._alpha_list = QListWidget()
        self._alpha_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._alpha_list.setMaximumHeight(180)
        gl.addWidget(self._alpha_list)
        llay.addWidget(grp)
        btn = QPushButton("▶  Calculate Cronbach's α"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_alpha)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        self._alpha_table = ResultsTable()
        rlay.addWidget(self._alpha_table, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Data listener ─────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        cols = list(df.columns) if df is not None else []
        for cb in (self._kappa_r1, self._kappa_r2, self._ba_m1, self._ba_m2):
            cb.clear(); cb.addItems(cols)
        for lb in (self._icc_list, self._alpha_list):
            lb.clear(); lb.addItems(cols)

    # ── Run Kappa ─────────────────────────────────────────────────────────────

    def _run_kappa(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        c1, c2 = self._kappa_r1.currentText(), self._kappa_r2.currentText()
        res = S.cohens_kappa(df[c1], df[c2])
        rows = [
            ("Cohen's Kappa",       round(res["kappa"], 4)),
            ("Weighted Kappa",      round(res["weighted_kappa"], 4) if not np.isnan(res["weighted_kappa"]) else "N/A"),
            ("Observed Agreement",  f"{res['observed_agreement']*100:.2f}%"),
            ("Interpretation",      res["interpretation"]),
            ("N",                   res["n"]),
        ]
        self._kappa_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))
        self._plot_kappa_agreement(df, c1, c2, res)
        self.status_message.emit(f"Kappa = {res['kappa']:.4f}  ({res['interpretation']})")

    def _plot_kappa_agreement(self, df, c1, c2, res):
        ax = self._kappa_plot.get_ax()
        ct = pd.crosstab(df[c1], df[c2])
        im = ax.imshow(ct.values, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(ct.columns)))
        ax.set_yticks(range(len(ct.index)))
        ax.set_xticklabels([str(c) for c in ct.columns], fontsize=8)
        ax.set_yticklabels([str(c) for c in ct.index], fontsize=8)
        for (i, j), v in np.ndenumerate(ct.values):
            ax.text(j, i, str(v), ha="center", va="center", fontsize=10, color="#f1f5f9")
        ax.set_xlabel(c2); ax.set_ylabel(c1)
        ax.set_title(f"Agreement Matrix  (κ = {res['kappa']:.4f})")
        self._kappa_plot.draw()

    # ── Run ICC ───────────────────────────────────────────────────────────────

    def _run_icc(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        cols = [it.text() for it in self._icc_list.selectedItems()]
        if len(cols) < 2:
            self.status_message.emit("Select ≥2 columns for ICC."); return
        res = S.icc_analysis(df[cols].dropna())

        icc_tbl = res.get("icc_table")
        if icc_tbl is not None and isinstance(icc_tbl, pd.DataFrame):
            self._icc_table.show_df(icc_tbl)
        else:
            rows = [("ICC Value", round(res.get("icc_value", np.nan), 4)),
                    ("N subjects", res.get("n_subjects")),
                    ("N raters",   res.get("n_raters"))]
            self._icc_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))

        # Scatter: rater 1 vs rater 2 (first two)
        ax = self._icc_plot.get_ax()
        d  = df[cols].dropna()
        ax.scatter(d.iloc[:, 0], d.iloc[:, 1], color="#0ea5e9", s=20, alpha=0.7)
        lim = [min(d.values.min(), d.values.min()),
               max(d.values.max(), d.values.max())]
        ax.plot(lim, lim, color="#f59e0b", lw=1.5, linestyle="--", label="Line of identity")
        ax.set_xlabel(cols[0]); ax.set_ylabel(cols[1] if len(cols) > 1 else "")
        ax.set_title(f"Rater Comparison  ({cols[0]} vs {cols[1]})")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        self._icc_plot.draw()
        self.status_message.emit("ICC analysis complete.")

    # ── Run Bland-Altman ──────────────────────────────────────────────────────

    def _run_ba(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        c1, c2 = self._ba_m1.currentText(), self._ba_m2.currentText()
        res = S.bland_altman(df[c1], df[c2])

        def _f(v): return round(v, 4) if not (isinstance(v, float) and np.isnan(v)) else "N/A"

        ci_m    = res["ci_mean"]
        ci_lo_u = res["ci_loa_upper"]
        ci_lo_l = res["ci_loa_lower"]

        rows = [
            ("N", res["n"]),
            ("Mean Difference (Bias)",   _f(res["mean_diff"])),
            ("SD of Differences",        _f(res["std_diff"])),
            ("95% CI of Bias",           f"{_f(ci_m[0])} to {_f(ci_m[1])}"),
            ("Upper LoA",                _f(res["loa_upper"])),
            ("95% CI Upper LoA",         f"{_f(ci_lo_u[0])} to {_f(ci_lo_u[1])}"),
            ("Lower LoA",                _f(res["loa_lower"])),
            ("95% CI Lower LoA",         f"{_f(ci_lo_l[0])} to {_f(ci_lo_l[1])}"),
            ("% Within LoA",             f"{_f(res['pct_within_loa'])}%"),
        ]
        self._ba_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))
        self._plot_ba(res, c1, c2)
        self.status_message.emit(f"Bland-Altman: bias={res['mean_diff']:.4f}, LoA [{res['loa_lower']:.4f}, {res['loa_upper']:.4f}]")

    def _plot_ba(self, res, c1, c2):
        ax = self._ba_plot.get_ax()
        mv   = res["mean_vals"]
        diff = res["diff"]
        md   = res["mean_diff"]
        loa_u= res["loa_upper"]
        loa_l= res["loa_lower"]

        ax.scatter(mv, diff, color="#0ea5e9", s=18, alpha=0.7, label="Observations")
        ax.axhline(md,    color="#22c55e", lw=2, linestyle="-",  label=f"Mean diff = {md:.4f}")
        ax.axhline(loa_u, color="#ef4444", lw=1.5, linestyle="--", label=f"+1.96 SD = {loa_u:.4f}")
        ax.axhline(loa_l, color="#ef4444", lw=1.5, linestyle="--", label=f"−1.96 SD = {loa_l:.4f}")

        # CI shading
        ci_m = res["ci_mean"]
        ci_u = res["ci_loa_upper"]
        ci_l = res["ci_loa_lower"]
        xlim = ax.get_xlim() if ax.get_xlim() != (0, 1) else (mv.min(), mv.max())
        ax.fill_between(xlim, [ci_m[0]]*2, [ci_m[1]]*2, color="#22c55e", alpha=0.1)
        ax.fill_between(xlim, [ci_u[0]]*2, [ci_u[1]]*2, color="#ef4444", alpha=0.1)
        ax.fill_between(xlim, [ci_l[0]]*2, [ci_l[1]]*2, color="#ef4444", alpha=0.1)

        ax.set_xlabel(f"Mean of {c1} & {c2}")
        ax.set_ylabel(f"Difference ({c1} − {c2})")
        ax.set_title("Bland-Altman Plot")
        ax.legend(fontsize=7, labelcolor="#f1f5f9", facecolor="#334155")
        self._ba_plot.draw()

    # ── Run Cronbach ──────────────────────────────────────────────────────────

    def _run_alpha(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        cols = [it.text() for it in self._alpha_list.selectedItems()]
        if len(cols) < 2:
            self.status_message.emit("Select ≥2 item columns."); return
        res = S.cronbach_alpha(df[cols])
        if "error" in res:
            self.status_message.emit(res["error"]); return
        rows = [
            ("Cronbach's Alpha",  round(res["cronbach_alpha"], 4)),
            ("Interpretation",   res["interpretation"]),
            ("Number of Items",  res["k_items"]),
            ("N",                res["n"]),
        ]
        self._alpha_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))
        self.status_message.emit(f"Cronbach's α = {res['cronbach_alpha']:.4f}  ({res['interpretation']})")
