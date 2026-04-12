"""
app/panel_correlation.py – Correlation Analysis panel.

Supports:
 • Pearson / Spearman / Kendall for two variables
 • Correlation matrix (heat-map)
 • Scatter plot matrix (pair plot)
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
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider, safe_run
from . import statistics as S


class CorrelationPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Correlation Analysis"))
        root.addWidget(Divider())

        tabs = QTabWidget()

        t1 = QWidget(); self._build_bivar_tab(t1)
        tabs.addTab(t1, "  Bivariate Correlation  ")

        t2 = QWidget(); self._build_matrix_tab(t2)
        tabs.addTab(t2, "  Correlation Matrix  ")

        root.addWidget(tabs, stretch=1)

    # ── Bivariate tab ─────────────────────────────────────────────────────────

    def _build_bivar_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)

        grp  = QGroupBox("Configuration")
        gl   = QFormLayout(grp)
        self._bv_x = QComboBox(); gl.addRow("Variable X:", self._bv_x)
        self._bv_y = QComboBox(); gl.addRow("Variable Y:", self._bv_y)
        self._bv_method = QComboBox()
        self._bv_method.addItems(["pearson", "spearman", "kendall"])
        gl.addRow("Method:", self._bv_method)
        llay.addWidget(grp)

        btn = QPushButton("▶  Compute Correlation"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_bivar)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        rtabs = QTabWidget()
        self._bv_table = ResultsTable()
        self._bv_plot  = PlotWidget(figsize=(7, 5))
        rtabs.addTab(self._bv_table, "📋  Results")
        rtabs.addTab(self._bv_plot,  "📈  Scatter Plot")
        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Matrix tab ────────────────────────────────────────────────────────────

    def _build_matrix_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)

        grp  = QGroupBox("Configuration")
        gl   = QVBoxLayout(grp)
        gl.addWidget(QLabel("Select numeric columns (Ctrl+click):"))
        self._mat_list = QListWidget()
        self._mat_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._mat_list.setMaximumHeight(200)
        gl.addWidget(self._mat_list)
        fl = QFormLayout()
        self._mat_method = QComboBox(); self._mat_method.addItems(["pearson", "spearman"])
        fl.addRow("Method:", self._mat_method)
        gl.addLayout(fl)
        llay.addWidget(grp)

        btn = QPushButton("▶  Compute Matrix"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_matrix)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right = QWidget(); rlay = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        rtabs = QTabWidget()
        self._mat_r_table = ResultsTable()
        self._mat_p_table = ResultsTable()
        self._heatmap_plot = PlotWidget(figsize=(7, 6))
        self._pairplot     = PlotWidget(figsize=(7, 6))
        rtabs.addTab(self._mat_r_table,  "📋  r-values")
        rtabs.addTab(self._mat_p_table,  "📋  p-values")
        rtabs.addTab(self._heatmap_plot, "🗺  Heat-map")
        rtabs.addTab(self._pairplot,     "📊  Pair Plot")
        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Data listener ─────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        cols = list(df.select_dtypes(include=[np.number]).columns) if df is not None else []
        for cb in (self._bv_x, self._bv_y):
            cb.clear(); cb.addItems(cols)
        self._mat_list.clear(); self._mat_list.addItems(cols)

    # ── Bivariate analysis ────────────────────────────────────────────────────

    @safe_run
    def _run_bivar(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        xc, yc = self._bv_x.currentText(), self._bv_y.currentText()
        method = self._bv_method.currentText()
        res = S.correlation(df[xc], df[yc], method=method)
        if "error" in res:
            self.status_message.emit(res["error"]); return

        ci = res["ci"]
        ci_str = f"{ci[0]:.4f} – {ci[1]:.4f}" if not np.isnan(ci[0]) else "N/A"
        rows = [
            ("Test",      res["test"]),
            ("N",         res["n"]),
            ("r",         round(res["r"], 4)),
            ("R²",        round(res["r_squared"], 4)),
            ("95% CI",    ci_str),
            ("p-value",   res["p_value"]),
            ("Significant", "Yes" if res["significant"] else "No"),
        ]
        self._bv_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))
        self._plot_bivar_scatter(res, xc, yc, method)
        self.status_message.emit(f"{method.capitalize()} r = {res['r']:.4f}, p = {res['p_value']:.4f}")

    def _plot_bivar_scatter(self, res, xc, yc, method):
        import matplotlib.pyplot as plt
        ax = self._bv_plot.get_ax()
        xv, yv = res["x_vals"], res["y_vals"]
        ax.scatter(xv, yv, color="#0ea5e9", s=20, alpha=0.7)
        # Regression line
        m, b = np.polyfit(xv, yv, 1)
        xsort = np.linspace(xv.min(), xv.max(), 200)
        ax.plot(xsort, m * xsort + b, color="#f59e0b", lw=2,
                label=f"r = {res['r']:.4f}  (p = {res['p_value']:.4f})")
        # CI band (Pearson only)
        if method == "pearson":
            n = len(xv)
            se = np.std(yv - (m * xv + b), ddof=2) * np.sqrt(
                1/n + (xsort - xv.mean())**2 / ((n-1)*np.var(xv, ddof=1)))
            from scipy.stats import t
            tc = t.ppf(0.975, df=n-2)
            ax.fill_between(xsort, m*xsort+b - tc*se, m*xsort+b + tc*se,
                            color="#0ea5e9", alpha=0.15, label="95% CI")
        ax.set_xlabel(xc); ax.set_ylabel(yc)
        ax.set_title(f"{method.capitalize()} Correlation: {xc} vs {yc}")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        self._bv_plot.draw()

    # ── Correlation matrix ────────────────────────────────────────────────────

    @safe_run
    def _run_matrix(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        sel_cols = [it.text() for it in self._mat_list.selectedItems()]
        if len(sel_cols) < 2:
            self.status_message.emit("Select ≥2 columns."); return
        method = self._mat_method.currentText()
        sub_df = df[sel_cols].select_dtypes(include=[np.number])
        res = S.correlation_matrix(sub_df, method=method)

        r_df   = res["corr_matrix"].round(4).reset_index()
        p_df   = res["p_matrix"].round(4).reset_index()
        self._mat_r_table.show_df(r_df)
        self._mat_p_table.show_df(p_df)
        self._plot_heatmap(res["corr_matrix"])
        self._plot_pairplot(sub_df)
        self.status_message.emit(f"Correlation matrix ({method}) computed for {len(sel_cols)} variables.")

    def _plot_heatmap(self, corr: pd.DataFrame):
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        ax = self._heatmap_plot.get_ax()
        cmap = LinearSegmentedColormap.from_list(
            "medstat", ["#ef4444", "#0f172a", "#0ea5e9"], N=256)
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.index)))
        ax.set_xticklabels(list(corr.columns), rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(list(corr.index), fontsize=8)
        for (i, j), v in np.ndenumerate(corr.values):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=8 if len(corr) <= 8 else 6,
                    color="#f1f5f9")
        self._heatmap_plot.figure.colorbar(im, ax=ax)
        ax.set_title("Correlation Heat-map")
        self._heatmap_plot.draw()

    def _plot_pairplot(self, df: pd.DataFrame):
        cols = list(df.columns)
        n    = len(cols)
        if n > 6:
            cols = cols[:6]
            n    = 6
        axes = self._pairplot.get_ax(n, n)
        if n == 1:
            axes = [[axes]]
        for i in range(n):
            for j in range(n):
                ax = axes[i * n + j] if isinstance(axes, list) else axes[i][j]
                if i == j:
                    ax.hist(df[cols[i]].dropna(), bins=15,
                            color="#0ea5e9", edgecolor="#334155", alpha=0.8)
                    ax.set_title(cols[i], fontsize=7, color="#f1f5f9")
                else:
                    xv = df[cols[j]].dropna()
                    yv = df[cols[i]].dropna()
                    n2 = min(len(xv), len(yv))
                    ax.scatter(xv[:n2], yv[:n2], color="#8b5cf6", s=5, alpha=0.6)
                if i < n - 1:
                    ax.set_xticklabels([])
                if j > 0:
                    ax.set_yticklabels([])
        self._pairplot.draw()
