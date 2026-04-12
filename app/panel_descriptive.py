"""
app/panel_descriptive.py – Descriptive Statistics panel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QListWidget, QAbstractItemView, QGroupBox,
    QSplitter, QScrollArea, QCheckBox, QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .core import data_store
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider, safe_run
from .statistics import quantitative_stats, categorical_stats, normality_tests


class DescriptivePanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Descriptive Statistics"))
        root.addWidget(Divider())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: controls ────────────────────────────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setMaximumWidth(310)
        lw   = QWidget()
        llay = QVBoxLayout(lw)
        llay.setContentsMargins(4, 4, 4, 4)
        llay.setSpacing(10)

        grp_cols = QGroupBox("Select Columns")
        gc_lay   = QVBoxLayout(grp_cols)
        gc_lay.addWidget(QLabel("Ctrl+click to select multiple:"))
        self._col_list = QListWidget()
        self._col_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._col_list.setMinimumHeight(160)
        gc_lay.addWidget(self._col_list)
        llay.addWidget(grp_cols)

        grp_opts = QGroupBox("Options")
        go_lay   = QVBoxLayout(grp_opts)
        self._chk_hist    = QCheckBox("Histogram")
        self._chk_hist.setChecked(True)
        self._chk_box     = QCheckBox("Box / Violin plot")
        self._chk_box.setChecked(True)
        self._chk_bar     = QCheckBox("Bar chart (categorical)")
        self._chk_bar.setChecked(True)
        self._chk_normal  = QCheckBox("Normality tests")
        self._chk_normal.setChecked(True)
        for w in (self._chk_hist, self._chk_box, self._chk_bar, self._chk_normal):
            go_lay.addWidget(w)
        llay.addWidget(grp_opts)

        run_btn = QPushButton("▶  Run Analysis")
        run_btn.setObjectName("primary")
        run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run)
        llay.addWidget(run_btn)
        llay.addStretch()
        left.setWidget(lw)

        # ── Right: tabs (results + plots) ─────────────────────────────────────
        self._tabs = QTabWidget()

        # Summary tab
        sum_w    = QWidget()
        sum_lay  = QVBoxLayout(sum_w)
        self._sum_table = ResultsTable()
        sum_lay.addWidget(self._sum_table)
        self._tabs.addTab(sum_w, "📋  Summary")

        # Frequency tab
        freq_w   = QWidget()
        freq_lay = QVBoxLayout(freq_w)
        self._freq_table = ResultsTable()
        freq_lay.addWidget(self._freq_table)
        self._tabs.addTab(freq_w, "🔢  Frequencies")

        # Normality tab
        norm_w   = QWidget()
        norm_lay = QVBoxLayout(norm_w)
        self._norm_table = ResultsTable()
        norm_lay.addWidget(self._norm_table)
        self._tabs.addTab(norm_w, "⚖  Normality")

        # Plot tabs
        self._hist_plot = PlotWidget(figsize=(8, 5))
        self._tabs.addTab(self._hist_plot, "📊  Histogram")

        self._box_plot = PlotWidget(figsize=(8, 5))
        self._tabs.addTab(self._box_plot, "📦  Box / Violin")

        self._bar_plot = PlotWidget(figsize=(8, 5))
        self._tabs.addTab(self._bar_plot, "📊  Bar Chart")

        self._qq_plot  = PlotWidget(figsize=(8, 5))
        self._tabs.addTab(self._qq_plot, "📈  Q-Q Plot")

        splitter.addWidget(left)
        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    # ── Data change handler ───────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        self._col_list.clear()
        if df is not None:
            self._col_list.addItems(list(df.columns))

    # ── Analysis ──────────────────────────────────────────────────────────────

    @safe_run
    def _run(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded.")
            return
        selected = [item.text() for item in self._col_list.selectedItems()]
        if not selected:
            self.status_message.emit("Select at least one column.")
            return

        quant_rows: list[dict]  = []
        cat_tables: list[pd.DataFrame] = []
        norm_rows:  list[dict]  = []

        for col in selected:
            col_type = data_store.column_types.get(col, "quantitative")
            s = df[col].dropna()

            if col_type in ("quantitative", "binary") and pd.api.types.is_numeric_dtype(s):
                r = quantitative_stats(df[col])
                row = {
                    "Variable":    col,
                    "n":           r.get("n"),
                    "Missing":     r.get("missing"),
                    "Mean ± SD":   f"{r['mean']:.3g} ± {r['std']:.3g}" if r.get("mean") is not None else "N/A",
                    "Median (IQR)": f"{r['median']:.3g} ({r['q1']:.3g}–{r['q3']:.3g})",
                    "Min":         f"{r['min']:.4g}",
                    "Max":         f"{r['max']:.4g}",
                    f"95% CI":     f"{r['ci_lower']:.3g} – {r['ci_upper']:.3g}",
                    "Skewness":    f"{r['skewness']:.3f}",
                }
                quant_rows.append(row)

                if self._chk_normal.isChecked():
                    nt = normality_tests(df[col])
                    for test_name, tres in nt.get("tests", {}).items():
                        norm_rows.append({
                            "Variable": col,
                            "Test":     test_name,
                            "Statistic": f"{tres['statistic']:.4f}",
                            "p": tres.get("p_value"),
                            "Normal?":  "Yes" if tres.get("normal") else "No",
                        })
            else:
                r = categorical_stats(df[col])
                t = r.get("table")
                if t is not None:
                    t.insert(0, "Variable", col)
                    cat_tables.append(t)

        # Summary table
        if quant_rows:
            self._sum_table.show_df(pd.DataFrame(quant_rows))
        elif not cat_tables:
            self.status_message.emit("No columns to summarise.")
            return

        # Frequency table
        if cat_tables:
            self._freq_table.show_df(pd.concat(cat_tables, ignore_index=True))
            self._tabs.setCurrentIndex(1)
        else:
            self._tabs.setCurrentIndex(0)

        # Normality table
        if norm_rows:
            self._norm_table.show_df(pd.DataFrame(norm_rows), p_cols=["p"])

        # Plots
        self._plot_histograms(df, selected)
        self._plot_boxplots(df, selected)
        self._plot_barcharts(df, selected)
        self._plot_qq(df, selected)

        self.status_message.emit(f"Descriptive analysis completed for: {', '.join(selected)}")

    # ── Plotting helpers ──────────────────────────────────────────────────────

    _PALETTE = ["#0ea5e9", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444",
                "#ec4899", "#14b8a6", "#f97316"]

    def _plot_histograms(self, df, cols):
        if not self._chk_hist.isChecked():
            return
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            return
        n = len(num_cols)
        ncols_plt = min(n, 3)
        nrows_plt = (n + ncols_plt - 1) // ncols_plt
        axes = self._hist_plot.get_ax(nrows_plt, ncols_plt)
        if n == 1:
            axes = [axes]
        for ax, col in zip(axes, num_cols):
            data = df[col].dropna()
            ax.hist(data, bins="auto", color=self._PALETTE[0], edgecolor="#334155", alpha=0.85)
            ax.axvline(data.mean(),   color="#f59e0b", lw=1.5, linestyle="--", label=f"Mean={data.mean():.3g}")
            ax.axvline(data.median(), color="#22c55e", lw=1.5, linestyle=":",  label=f"Median={data.median():.3g}")
            ax.set_title(col, fontsize=9, color="#f1f5f9")
            ax.set_xlabel("Value"); ax.set_ylabel("Frequency")
            ax.legend(fontsize=7, labelcolor="#f1f5f9", facecolor="#334155")
        for ax in axes[n:]:
            ax.set_visible(False)
        self._hist_plot.draw()

    def _plot_boxplots(self, df, cols):
        if not self._chk_box.isChecked():
            return
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            return
        ax = self._box_plot.get_ax()
        parts = ax.violinplot([df[c].dropna().values for c in num_cols],
                              showmedians=True, showextrema=True)
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(self._PALETTE[i % len(self._PALETTE)])
            pc.set_alpha(0.7)
        parts["cmedians"].set_color("#f59e0b")
        parts["cmins"].set_color("#94a3b8")
        parts["cmaxes"].set_color("#94a3b8")
        parts["cbars"].set_color("#94a3b8")
        ax.set_xticks(range(1, len(num_cols) + 1))
        ax.set_xticklabels(num_cols, rotation=25, ha="right", fontsize=8)
        ax.set_ylabel("Value")
        ax.set_title("Distribution (Violin Plot)")
        self._box_plot.draw()

    def _plot_barcharts(self, df, cols):
        if not self._chk_bar.isChecked():
            return
        cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])
                    or data_store.column_types.get(c) == "categorical"]
        if not cat_cols:
            return
        n = len(cat_cols)
        ncols_plt = min(n, 2)
        nrows_plt = (n + ncols_plt - 1) // ncols_plt
        axes = self._bar_plot.get_ax(nrows_plt, ncols_plt)
        if n == 1:
            axes = [axes]
        for ax, col in zip(axes, cat_cols):
            vc = df[col].value_counts()
            pct = (vc / vc.sum() * 100).round(1)
            bars = ax.bar(range(len(vc)), vc.values,
                          color=self._PALETTE[:len(vc)], edgecolor="#334155", alpha=0.85)
            ax.set_xticks(range(len(vc)))
            ax.set_xticklabels([str(v) for v in vc.index], rotation=30, ha="right", fontsize=8)
            ax.set_title(col, fontsize=9, color="#f1f5f9")
            ax.set_ylabel("Count")
            for bar, p in zip(bars, pct):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                        f"{p}%", ha="center", va="bottom", fontsize=7, color="#f1f5f9")
        self._bar_plot.draw()

    def _plot_qq(self, df, cols):
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            return
        n = len(num_cols)
        ncols_plt = min(n, 3)
        nrows_plt = (n + ncols_plt - 1) // ncols_plt
        axes = self._qq_plot.get_ax(nrows_plt, ncols_plt)
        if n == 1:
            axes = [axes]
        from scipy import stats as sci_stats
        for ax, col in zip(axes, num_cols):
            data = df[col].dropna().values
            (osm, osr), (slope, intercept, r) = sci_stats.probplot(data)
            ax.scatter(osm, osr, color=self._PALETTE[0], s=15, alpha=0.7, label="Observed")
            ax.plot(osm, slope * np.asarray(osm) + intercept, color="#f59e0b",
                    lw=1.5, label=f"R²={r**2:.3f}")
            ax.set_title(f"Q-Q: {col}", fontsize=9, color="#f1f5f9")
            ax.set_xlabel("Theoretical Quantiles")
            ax.set_ylabel("Sample Quantiles")
            ax.legend(fontsize=7, labelcolor="#f1f5f9", facecolor="#334155")
        self._qq_plot.draw()
