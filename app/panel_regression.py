"""
app/panel_regression.py – Regression Analysis panel.

Supports: Simple Linear · Multiple Linear · Binary Logistic · Poisson
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


_REG_TYPES = [
    "Simple Linear Regression",
    "Multiple Linear Regression",
    "Binary Logistic Regression",
    "Poisson Regression",
]


class RegressionPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Regression Analysis"))
        root.addWidget(Divider())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left controls ─────────────────────────────────────────────────────
        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(330)
        lw   = QWidget()
        llay = QVBoxLayout(lw)
        llay.setContentsMargins(4, 4, 4, 4)
        llay.setSpacing(10)

        grp_type = QGroupBox("Regression Type")
        gt_lay   = QVBoxLayout(grp_type)
        self._type_combo = QComboBox()
        self._type_combo.addItems(_REG_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        gt_lay.addWidget(self._type_combo)
        llay.addWidget(grp_type)

        grp_vars = QGroupBox("Variables")
        gv_lay   = QFormLayout(grp_vars)

        self._outcome_combo = QComboBox()
        gv_lay.addRow("Outcome (Y):", self._outcome_combo)

        self._pred_list = QListWidget()
        self._pred_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._pred_list.setMaximumHeight(160)
        self._pred_hint = QLabel("Ctrl+click for multiple (MLR / Logistic).")
        self._pred_hint.setObjectName("muted"); self._pred_hint.setWordWrap(True)
        gv_lay.addRow("Predictors (X):", self._pred_list)
        gv_lay.addRow(self._pred_hint)
        llay.addWidget(grp_vars)

        run_btn = QPushButton("▶  Fit Model")
        run_btn.setObjectName("primary"); run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run)
        llay.addWidget(run_btn)
        llay.addStretch()
        left.setWidget(lw)

        # ── Right results ─────────────────────────────────────────────────────
        right = QWidget()
        rlay  = QVBoxLayout(right)
        rlay.setContentsMargins(8, 0, 0, 0)

        rtabs = QTabWidget()
        self._coef_table   = ResultsTable()
        self._model_table  = ResultsTable()
        self._vif_table    = ResultsTable()
        self._diag_plot    = PlotWidget(figsize=(7, 5))
        self._scatter_plot = PlotWidget(figsize=(7, 5))

        rtabs.addTab(self._coef_table,   "📋  Coefficients")
        rtabs.addTab(self._model_table,  "📋  Model Fit")
        rtabs.addTab(self._vif_table,    "📋  VIF / Collinearity")
        rtabs.addTab(self._diag_plot,    "📊  Diagnostics")
        rtabs.addTab(self._scatter_plot, "📈  Scatter / ROC")

        rlay.addWidget(rtabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    # ── Listeners ─────────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        cols = list(df.columns) if df is not None else []
        self._outcome_combo.clear(); self._outcome_combo.addItems(cols)
        self._pred_list.clear(); self._pred_list.addItems(cols)

    def _on_type_changed(self, text: str):
        multi = text != "Simple Linear Regression"
        self._pred_hint.setVisible(multi)

    # ── Run ───────────────────────────────────────────────────────────────────

    def _run(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        reg_type  = self._type_combo.currentText()
        outcome   = self._outcome_combo.currentText()
        sel_preds = [it.text() for it in self._pred_list.selectedItems()]
        if not sel_preds:
            self.status_message.emit("Select at least one predictor."); return

        y = df[outcome]

        if reg_type == "Simple Linear Regression":
            x = df[sel_preds[0]]
            res = S.simple_linear_regression(x, y)
            if "error" in res:
                self.status_message.emit(res["error"]); return
            self._show_linear(res)
            self._plot_scatter_linear(res, sel_preds[0], outcome)
            self._plot_diagnostics_linear(res)
            msg = (f"R² = {res['r_squared']:.4f}, "
                   f"slope p = {res['slope']:.4g}")

        elif reg_type == "Multiple Linear Regression":
            X = df[sel_preds]
            res = S.multiple_linear_regression(X, y)
            if "error" in res:
                self.status_message.emit(res["error"]); return
            self._show_linear(res)
            self._plot_diagnostics_linear(res)
            msg = (f"R² = {res['r_squared']:.4f}, "
                   f"Adj-R² = {res['adj_r_squared']:.4f}, "
                   f"F p = {res['f_p']:.4g}")

        elif reg_type == "Binary Logistic Regression":
            X = df[sel_preds]
            res = S.logistic_regression(X, y)
            if "error" in res:
                self.status_message.emit(res["error"]); return
            self._show_logistic(res)
            self._plot_logistic_roc(res)
            msg = (f"AUC = {res['auc']:.4f}, "
                   f"AIC = {res['aic']:.2f}, "
                   f"McFadden R² = {res['pseudo_r2_mcfadden']:.4f}")

        elif reg_type == "Poisson Regression":
            X = df[sel_preds]
            res = S.poisson_regression(X, y)
            if "error" in res:
                self.status_message.emit(res["error"]); return
            self._show_poisson(res)
            msg = f"AIC = {res['aic']:.2f}, Deviance = {res['deviance']:.2f}"

        else:
            msg = "Unknown regression type."

        self.status_message.emit(f"{reg_type} fitted.  {msg}")

    # ── Display helpers ───────────────────────────────────────────────────────

    def _show_linear(self, res: dict):
        tbl = res.get("params_table")
        if tbl is not None:
            self._coef_table.show_df(tbl, p_cols=["p"])

        model_rows = []
        for k in ("n", "r", "r_squared", "adj_r_squared", "f_stat", "f_p", "aic", "bic", "k"):
            if k in res:
                model_rows.append({"Metric": k, "Value": res[k]})
        if model_rows:
            self._model_table.show_df(pd.DataFrame(model_rows))

        vif = res.get("vif_table")
        if vif is not None:
            self._vif_table.show_df(vif)

    def _show_logistic(self, res: dict):
        tbl = res.get("params_table")
        if tbl is not None:
            self._coef_table.show_df(tbl, p_cols=["p"])
        model_rows = [
            {"Metric": "N",           "Value": res.get("n")},
            {"Metric": "Predictors",  "Value": res.get("k")},
            {"Metric": "AUC",         "Value": round(res.get("auc", np.nan), 4)},
            {"Metric": "AIC",         "Value": round(res.get("aic", np.nan), 2)},
            {"Metric": "BIC",         "Value": round(res.get("bic", np.nan), 2)},
            {"Metric": "McFadden R²", "Value": round(res.get("pseudo_r2_mcfadden", np.nan), 4)},
            {"Metric": "Log-Likelihood", "Value": round(res.get("log_likelihood", np.nan), 2)},
        ]
        self._model_table.show_df(pd.DataFrame(model_rows))
        # Confusion matrix
        cm = res.get("confusion_matrix")
        if cm is not None:
            cm_df = pd.DataFrame(cm, index=["Actual 0", "Actual 1"],
                                  columns=["Pred 0", "Pred 1"])
            self._vif_table.show_df(cm_df)

    def _show_poisson(self, res: dict):
        tbl = res.get("params_table")
        if tbl is not None:
            self._coef_table.show_df(tbl, p_cols=["p"])
        model_rows = [
            {"Metric": "N",         "Value": res.get("n")},
            {"Metric": "AIC",       "Value": round(res.get("aic", np.nan), 2)},
            {"Metric": "BIC",       "Value": round(res.get("bic", np.nan), 2)},
            {"Metric": "Deviance",  "Value": round(res.get("deviance", np.nan), 2)},
        ]
        self._model_table.show_df(pd.DataFrame(model_rows))

    # ── Plots ─────────────────────────────────────────────────────────────────

    def _plot_scatter_linear(self, res, xname, yname):
        ax = self._scatter_plot.get_ax()
        xv, yv = res["x_vals"], res["y_vals"]
        fitted = res["fitted"]
        ax.scatter(xv, yv, color="#0ea5e9", s=20, alpha=0.7, label="Observed")
        sort_idx = np.argsort(xv)
        ax.plot(xv[sort_idx], fitted[sort_idx], color="#f59e0b", lw=2,
                label=f"Fit: y = {res['intercept']:.3g} + {res['slope']:.3g}·x")
        ax.set_xlabel(xname); ax.set_ylabel(yname)
        ax.set_title(f"Simple Linear Regression  (R² = {res['r_squared']:.4f})")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        self._scatter_plot.draw()

    def _plot_diagnostics_linear(self, res):
        residuals = res.get("residuals")
        fitted    = res.get("fitted")
        if residuals is None:
            return
        axes = self._diag_plot.get_ax(2, 2)
        ax1, ax2, ax3, ax4 = axes

        # Residuals vs fitted
        ax1.scatter(fitted, residuals, color="#0ea5e9", s=12, alpha=0.6)
        ax1.axhline(0, color="#f59e0b", lw=1.5, linestyle="--")
        ax1.set_xlabel("Fitted"); ax1.set_ylabel("Residuals")
        ax1.set_title("Residuals vs Fitted")

        # Q-Q
        from scipy import stats as sci_s
        (osm, osr), (slope, intercept, r) = sci_s.probplot(residuals)
        ax2.scatter(osm, osr, color="#8b5cf6", s=12, alpha=0.7)
        ax2.plot(osm, slope * np.asarray(osm) + intercept, color="#f59e0b", lw=1.5)
        ax2.set_title("Normal Q-Q"); ax2.set_xlabel("Theoretical"); ax2.set_ylabel("Sample")

        # Scale-location
        ax3.scatter(fitted, np.sqrt(np.abs(residuals)), color="#22c55e", s=12, alpha=0.6)
        ax3.set_xlabel("Fitted"); ax3.set_ylabel("√|Residuals|")
        ax3.set_title("Scale-Location")

        # Histogram of residuals
        ax4.hist(residuals, bins="auto", color="#0ea5e9", edgecolor="#334155", alpha=0.8)
        ax4.set_xlabel("Residuals"); ax4.set_ylabel("Frequency")
        ax4.set_title("Residual Distribution")

        self._diag_plot.draw()

    def _plot_logistic_roc(self, res):
        proba = res.get("predicted_proba")
        y_true = res.get("y_true")
        if proba is None or y_true is None:
            return
        from sklearn.metrics import roc_curve, auc
        fpr, tpr, _ = roc_curve(y_true, proba)
        auc_val = auc(fpr, tpr)
        ax = self._scatter_plot.get_ax()
        ax.plot(fpr, tpr, color="#0ea5e9", lw=2, label=f"AUC = {auc_val:.4f}")
        ax.plot([0, 1], [0, 1], color="#475569", lw=1, linestyle="--")
        ax.fill_between(fpr, tpr, alpha=0.15, color="#0ea5e9")
        ax.set_xlabel("1 − Specificity (FPR)")
        ax.set_ylabel("Sensitivity (TPR)")
        ax.set_title("ROC Curve – Logistic Regression")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        self._scatter_plot.draw()

        # Diagnostics: residuals
        from sklearn.metrics import confusion_matrix
        axes = self._diag_plot.get_ax(1, 2)
        ax1, ax2 = axes
        ax1.hist(proba[y_true == 0], bins=20, alpha=0.7, color="#0ea5e9", label="Actual 0")
        ax1.hist(proba[y_true == 1], bins=20, alpha=0.7, color="#8b5cf6", label="Actual 1")
        ax1.set_xlabel("Predicted Probability"); ax1.set_ylabel("Count")
        ax1.set_title("Predicted Probability Distribution")
        ax1.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")

        cm = confusion_matrix(y_true, (proba >= 0.5).astype(int))
        ax2.imshow(cm, cmap="Blues", aspect="auto")
        ax2.set_xticks([0, 1]); ax2.set_yticks([0, 1])
        ax2.set_xticklabels(["Pred 0", "Pred 1"]); ax2.set_yticklabels(["Act 0", "Act 1"])
        for (i, j), v in np.ndenumerate(cm):
            ax2.text(j, i, str(v), ha="center", va="center", fontsize=12, color="#f1f5f9")
        ax2.set_title("Confusion Matrix (threshold = 0.5)")
        self._diag_plot.draw()
