"""
app/panel_survival.py – Survival Analysis panel.

Includes:
 • Kaplan-Meier curves (with optional grouping)
 • Log-rank test
 • Cox Proportional Hazards Regression
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QListWidget, QAbstractItemView, QGroupBox,
    QSplitter, QTabWidget, QScrollArea, QFormLayout, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .core import data_store
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider
from . import statistics as S


class SurvivalPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Survival Analysis"))
        root.addWidget(Divider())

        tabs = QTabWidget()
        t1 = QWidget(); self._build_km_tab(t1)
        tabs.addTab(t1, "  Kaplan-Meier  ")

        t2 = QWidget(); self._build_cox_tab(t2)
        tabs.addTab(t2, "  Cox Regression  ")

        root.addWidget(tabs, stretch=1)

    # ── Kaplan-Meier tab ──────────────────────────────────────────────────────

    def _build_km_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)

        grp = QGroupBox("Configuration")
        gl  = QFormLayout(grp)
        self._km_time   = QComboBox(); gl.addRow("Time column:", self._km_time)
        self._km_event  = QComboBox(); gl.addRow("Event column (0/1):", self._km_event)
        self._km_group  = QComboBox()
        self._km_group.addItem("(None – overall KM)")
        gl.addRow("Optional group:", self._km_group)
        llay.addWidget(grp)

        btn = QPushButton("▶  Run Kaplan-Meier"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_km)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right  = QWidget()
        rlay   = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        rtabs  = QTabWidget()
        self._km_table = ResultsTable()
        self._km_plot  = PlotWidget(figsize=(7, 5))
        rtabs.addTab(self._km_table, "📋  Statistics")
        rtabs.addTab(self._km_plot,  "📈  KM Curve")
        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Cox tab ───────────────────────────────────────────────────────────────

    def _build_cox_tab(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(300)
        lw   = QWidget()
        llay = QVBoxLayout(lw); llay.setContentsMargins(4, 4, 4, 4); llay.setSpacing(8)

        grp = QGroupBox("Configuration")
        gl  = QFormLayout(grp)
        self._cox_time  = QComboBox(); gl.addRow("Time column:", self._cox_time)
        self._cox_event = QComboBox(); gl.addRow("Event column:", self._cox_event)
        llay.addWidget(grp)

        grp2 = QGroupBox("Covariates (Ctrl+click)")
        gl2  = QVBoxLayout(grp2)
        self._cox_cov_list = QListWidget()
        self._cox_cov_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._cox_cov_list.setMaximumHeight(180)
        gl2.addWidget(self._cox_cov_list)
        llay.addWidget(grp2)

        btn = QPushButton("▶  Fit Cox Model"); btn.setObjectName("primary")
        btn.setMinimumHeight(34); btn.clicked.connect(self._run_cox)
        llay.addWidget(btn); llay.addStretch(); left.setWidget(lw)

        right   = QWidget()
        rlay    = QVBoxLayout(right); rlay.setContentsMargins(8, 0, 0, 0)
        rtabs   = QTabWidget()
        self._cox_table    = ResultsTable()
        self._cox_fit_tbl  = ResultsTable()
        self._cox_plot     = PlotWidget(figsize=(7, 5))
        rtabs.addTab(self._cox_table,    "📋  Coefficients (HR)")
        rtabs.addTab(self._cox_fit_tbl,  "📋  Model Fit")
        rtabs.addTab(self._cox_plot,     "📊  Baseline Hazard")
        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1); lay.addWidget(splitter, stretch=1)

    # ── Data listener ─────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        cols = list(df.columns) if df is not None else []
        for cb in (self._km_time, self._km_event,
                   self._cox_time, self._cox_event):
            cb.clear(); cb.addItems(cols)
        # Group combo keeps "(None)" option
        self._km_group.clear()
        self._km_group.addItem("(None – overall KM)")
        self._km_group.addItems(cols)
        self._cox_cov_list.clear()
        self._cox_cov_list.addItems(cols)

    # ── Run KM ────────────────────────────────────────────────────────────────

    def _run_km(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        tc, ec = self._km_time.currentText(), self._km_event.currentText()
        gc_txt = self._km_group.currentText()
        gc = None if gc_txt.startswith("(None") else gc_txt

        try:
            if gc:
                res = S.kaplan_meier(df[tc], df[ec], df[gc])
            else:
                res = S.kaplan_meier(df[tc], df[ec])
        except Exception as exc:
            self.status_message.emit(str(exc)); return

        if "error" in res:
            self.status_message.emit(res["error"]); return

        # Build summary table
        rows = []
        for grp_name, info in res["groups"].items():
            rows.append({
                "Group":   grp_name,
                "N":       info.get("n", "—"),
                "Median Survival": round(info["median"], 4) if not np.isnan(info["median"]) else "Not reached",
            })
        df_sum = pd.DataFrame(rows)

        lr = res.get("logrank")
        if lr:
            df_sum = pd.concat([df_sum, pd.DataFrame([{
                "Group": "Log-rank p-value",
                "N": "—",
                "Median Survival": round(lr["p_value"], 4),
            }])], ignore_index=True)

        self._km_table.show_df(df_sum)
        self._plot_km(res)

        msg = "KM complete."
        if lr:
            msg += f"  Log-rank p = {lr['p_value']:.4f}"
        self.status_message.emit(msg)

    def _plot_km(self, res: dict):
        ax = self._km_plot.get_ax()
        palette = ["#0ea5e9", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444"]
        for i, (grp_name, info) in enumerate(res["groups"].items()):
            kmf = info["kmf"]
            sf  = kmf.survival_function_
            color = palette[i % len(palette)]
            ax.step(sf.index, sf.iloc[:, 0], where="post", lw=2,
                    color=color, label=str(grp_name))
            # CI
            try:
                ci_df = kmf.confidence_interval_survival_function_
                ax.fill_between(ci_df.index,
                                ci_df.iloc[:, 0], ci_df.iloc[:, 1],
                                alpha=0.15, step="post", color=color)
            except Exception:
                pass

        ax.set_xlabel("Time"); ax.set_ylabel("Survival Probability")
        ax.set_ylim(-0.05, 1.05); ax.set_title("Kaplan-Meier Survival Curve")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")

        lr = res.get("logrank")
        if lr:
            ax.text(0.98, 0.05, f"Log-rank p = {lr['p_value']:.4f}",
                    transform=ax.transAxes, ha="right", fontsize=9, color="#f59e0b")
        self._km_plot.draw()

    # ── Run Cox ───────────────────────────────────────────────────────────────

    def _run_cox(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        tc  = self._cox_time.currentText()
        ec  = self._cox_event.currentText()
        cov = [it.text() for it in self._cox_cov_list.selectedItems()]
        if not cov:
            self.status_message.emit("Select ≥1 covariate."); return

        res = S.cox_regression(df, tc, ec, cov)
        if "error" in res:
            self.status_message.emit(res["error"]); return

        # Coefficients table
        params = res["params_table"]
        if isinstance(params, pd.DataFrame):
            p_reset = params.reset_index()
            self._cox_table.show_df(p_reset, p_cols=["p"])

        fit_rows = [
            ("N", res["n"]),
            ("Events", res["n_events"]),
            ("Concordance Index (C)", round(res["concordance_index"], 4)),
            ("AIC (partial)", round(res["aic"], 2)),
        ]
        self._cox_fit_tbl.show_df(pd.DataFrame(fit_rows, columns=["Metric", "Value"]))

        # Baseline hazard plot
        try:
            cph = res["cph"]
            ax  = self._cox_plot.get_ax()
            bh  = cph.baseline_cumulative_hazard_
            ax.step(bh.index, bh.iloc[:, 0], where="post", lw=2, color="#0ea5e9")
            ax.set_xlabel("Time")
            ax.set_ylabel("Cumulative Baseline Hazard")
            ax.set_title("Baseline Cumulative Hazard")
            self._cox_plot.draw()
        except Exception:
            pass

        self.status_message.emit(
            f"Cox model: N={res['n']}, events={res['n_events']}, "
            f"C-index={res['concordance_index']:.4f}")
