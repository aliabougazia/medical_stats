"""
app/panel_diagnostic.py – Diagnostic Tests panel (2×2 table entry + ROC).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QGroupBox, QSplitter, QTabWidget, QComboBox,
    QScrollArea, QFormLayout, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .core import data_store, format_ci
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider, safe_run
from .statistics import diagnostic_metrics, roc_analysis


class DiagnosticPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        data_store.add_listener(self._on_data_change)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("Diagnostic Test Evaluation"))
        root.addWidget(Divider())

        tabs = QTabWidget()

        # ── Tab 1: Manual 2×2 entry ───────────────────────────────────────────
        t1 = QWidget()
        self._build_tab_manual(t1)
        tabs.addTab(t1, "  2×2 Table Entry  ")

        # ── Tab 2: ROC Curve ──────────────────────────────────────────────────
        t2 = QWidget()
        self._build_tab_roc(t2)
        tabs.addTab(t2, "  ROC Curve  ")

        root.addWidget(tabs, stretch=1)

    # ─────────────────────────────── Tab 1: Manual ───────────────────────────

    def _build_tab_manual(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: entry form
        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(360)
        lw   = QWidget()
        llay = QVBoxLayout(lw)
        llay.setContentsMargins(4, 4, 4, 4)
        llay.setSpacing(10)

        grp = QGroupBox("Enter 2×2 Contingency Table")
        g_lay = QVBoxLayout(grp)

        # Table layout visual
        tbl_widget = QFrame()
        tbl_widget.setStyleSheet("background:#1e293b; border-radius:6px;")
        tbl_lay = QVBoxLayout(tbl_widget)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(""), stretch=1)
        lbl_dp = QLabel("Disease +"); lbl_dp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_dn = QLabel("Disease −"); lbl_dn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(lbl_dp, stretch=1); header_row.addWidget(lbl_dn, stretch=1)
        tbl_lay.addLayout(header_row)

        row_tp = QHBoxLayout()
        lbl_tp = QLabel("Test +"); lbl_tp.setFixedWidth(60)
        self._tp = QSpinBox(); self._tp.setRange(0, 999999); self._tp.setValue(80)
        self._fp = QSpinBox(); self._fp.setRange(0, 999999); self._fp.setValue(10)
        row_tp.addWidget(lbl_tp); row_tp.addWidget(self._tp); row_tp.addWidget(self._fp)
        tbl_lay.addLayout(row_tp)

        row_fn = QHBoxLayout()
        lbl_fn = QLabel("Test −"); lbl_fn.setFixedWidth(60)
        self._fn = QSpinBox(); self._fn.setRange(0, 999999); self._fn.setValue(20)
        self._tn = QSpinBox(); self._tn.setRange(0, 999999); self._tn.setValue(90)
        row_fn.addWidget(lbl_fn); row_fn.addWidget(self._fn); row_fn.addWidget(self._tn)
        tbl_lay.addLayout(row_fn)
        g_lay.addWidget(tbl_widget)

        hint = QLabel("TP=80, FP=10, FN=20, TN=90  (example)")
        hint.setObjectName("muted")
        g_lay.addWidget(hint)

        run_btn = QPushButton("▶  Calculate Metrics")
        run_btn.setObjectName("primary"); run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run_manual)
        g_lay.addWidget(run_btn)
        llay.addWidget(grp)
        llay.addStretch()
        left.setWidget(lw)

        # Right
        right = QWidget()
        rlay  = QVBoxLayout(right)
        rlay.setContentsMargins(8, 0, 0, 0)
        self._manual_table = ResultsTable()
        self._manual_plot  = PlotWidget(figsize=(6, 4))
        rlay.addWidget(self._manual_table, stretch=1)
        rlay.addWidget(self._manual_plot, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter, stretch=1)

    # ─────────────────────────────── Tab 2: ROC ──────────────────────────────

    def _build_tab_roc(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left
        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(310)
        lw   = QWidget()
        llay = QVBoxLayout(lw)
        llay.setContentsMargins(4, 4, 4, 4)
        llay.setSpacing(10)

        grp = QGroupBox("ROC Configuration")
        g_lay = QFormLayout(grp)
        self._roc_score_col  = QComboBox()
        self._roc_label_col  = QComboBox()
        self._roc_neg_val    = QComboBox()   # which value maps to 0
        self._roc_pos_val    = QComboBox()   # which value maps to 1
        g_lay.addRow("Score / Predictor:", self._roc_score_col)
        g_lay.addRow("Label column:", self._roc_label_col)
        g_lay.addRow("Negative class (= 0):", self._roc_neg_val)
        g_lay.addRow("Positive class (= 1):", self._roc_pos_val)
        hint2 = QLabel(
            "Select which label value is the positive class (e.g. Malignant = 1). "
            "Any column type is accepted — values will be encoded automatically."
        )
        hint2.setObjectName("muted"); hint2.setWordWrap(True)
        g_lay.addRow(hint2)
        llay.addWidget(grp)
        # Repopulate class selectors when label column changes
        self._roc_label_col.currentTextChanged.connect(self._refresh_class_combos)

        roc_run = QPushButton("▶  Compute ROC Curve")
        roc_run.setObjectName("primary"); roc_run.setMinimumHeight(36)
        roc_run.clicked.connect(self._run_roc)
        llay.addWidget(roc_run)
        llay.addStretch()
        left.setWidget(lw)

        # Right: tabs
        roc_tabs  = QTabWidget()
        self._roc_metrics_table = ResultsTable()
        roc_tabs.addTab(self._roc_metrics_table, "📋  Metrics")

        self._roc_curve_table = ResultsTable()
        roc_tabs.addTab(self._roc_curve_table, "🔢  Curve Data")

        self._roc_plot  = PlotWidget(figsize=(6, 5))
        roc_tabs.addTab(self._roc_plot, "📈  ROC Curve")

        splitter.addWidget(left); splitter.addWidget(roc_tabs)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter, stretch=1)

    # ── Data listener ─────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        for combo in (self._roc_score_col, self._roc_label_col):
            combo.clear()
            if df is not None:
                combo.addItems(list(df.columns))
        self._refresh_class_combos()

    def _refresh_class_combos(self):
        """Populate neg/pos class combos with unique values from the label column."""
        df = data_store.df
        self._roc_neg_val.clear()
        self._roc_pos_val.clear()
        if df is None:
            return
        col = self._roc_label_col.currentText()
        if not col or col not in df.columns:
            return
        unique_vals = [str(v) for v in sorted(df[col].dropna().unique(), key=str)]
        self._roc_neg_val.addItems(unique_vals)
        self._roc_pos_val.addItems(unique_vals)
        # Default: first value = negative, last = positive
        if len(unique_vals) >= 2:
            self._roc_neg_val.setCurrentIndex(0)
            self._roc_pos_val.setCurrentIndex(len(unique_vals) - 1)

    # ── Manual 2×2 analysis ───────────────────────────────────────────────────

    @safe_run
    def _run_manual(self):
        tp = self._tp.value(); fp = self._fp.value()
        fn = self._fn.value(); tn = self._tn.value()
        res = diagnostic_metrics(tp, fp, fn, tn)
        if "error" in res:
            self.status_message.emit(res["error"]); return

        def _pct(v): return f"{v*100:.2f}%" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "N/A"
        def _ci_pct(ci_tuple):
            lo, hi = ci_tuple
            return format_ci(lo, hi, pct=True)

        rows = [
            ("Sensitivity (Recall)",   _pct(res["sensitivity"]),  _ci_pct(res["sensitivity_ci"])),
            ("Specificity",            _pct(res["specificity"]),  _ci_pct(res["specificity_ci"])),
            ("PPV (Precision)",        _pct(res["ppv"]),          _ci_pct(res["ppv_ci"])),
            ("NPV",                    _pct(res["npv"]),          _ci_pct(res["npv_ci"])),
            ("Diagnostic Accuracy",    _pct(res["accuracy"]),     _ci_pct(res["accuracy_ci"])),
            ("F1 Score",               f"{res['f1_score']:.4f}" if res["f1_score"] is not None else "N/A", "—"),
            ("LR+  (Positive LR)",     f"{res['lr_positive']:.3f}" if not np.isnan(res["lr_positive"]) else "N/A", "—"),
            ("LR−  (Negative LR)",     f"{res['lr_negative']:.3f}" if not np.isnan(res["lr_negative"]) else "N/A", "—"),
            ("Diagnostic Odds Ratio",  f"{res['diagnostic_odds_ratio']:.3f}" if not np.isnan(res["diagnostic_odds_ratio"]) else "N/A", "—"),
            ("Prevalence",             _pct(res["prevalence"]),   "—"),
            ("Total N",                str(res["total"]),         "—"),
        ]
        df_res = pd.DataFrame(rows, columns=["Metric", "Value", "95% CI"])
        self._manual_table.show_df(df_res)

        # Spider / waterfall plot
        self._plot_manual_spider(res)
        self.status_message.emit("Diagnostic metrics calculated.")

    def _plot_manual_spider(self, res: dict):
        ax = self._manual_plot.get_ax()
        metrics = {
            "Sensitivity": res["sensitivity"],
            "Specificity": res["specificity"],
            "PPV":         res["ppv"],
            "NPV":         res["npv"],
            "Accuracy":    res["accuracy"],
        }
        names  = list(metrics.keys())
        values = [v if v is not None and not np.isnan(v) else 0 for v in metrics.values()]
        colors = ["#0ea5e9", "#8b5cf6", "#22c55e", "#f59e0b", "#ec4899"]
        bars   = ax.barh(names, [v * 100 for v in values], color=colors, alpha=0.85, edgecolor="#334155")
        for bar, v in zip(bars, values):
            ax.text(min(v * 100 + 1, 99), bar.get_y() + bar.get_height()/2,
                    f"{v*100:.1f}%", va="center", fontsize=9, color="#f1f5f9")
        ax.set_xlim(0, 110)
        ax.set_xlabel("Percentage (%)")
        ax.set_title("Diagnostic Performance Overview")
        self._manual_plot.draw()

    # ── ROC analysis ──────────────────────────────────────────────────────────

    @safe_run
    def _run_roc(self):
        df = data_store.df
        if df is None:
            self.status_message.emit("No data loaded."); return
        score_col = self._roc_score_col.currentText()
        label_col = self._roc_label_col.currentText()
        if not score_col or not label_col:
            self.status_message.emit("Select both score and label columns."); return

        neg_str = self._roc_neg_val.currentText()
        pos_str = self._roc_pos_val.currentText()
        if neg_str == pos_str:
            self.status_message.emit("Negative and positive classes must be different."); return

        # Encode label column: pos_val → 1, neg_val → 0, anything else → NaN
        raw_label = df[label_col].astype(str)
        encoded = raw_label.map(lambda v: 1 if v == pos_str else (0 if v == neg_str else np.nan))
        valid_mask = encoded.notna()
        n_excluded = (~valid_mask).sum()
        encoded   = encoded[valid_mask].astype(int)
        score_ser = df.loc[valid_mask, score_col]

        if n_excluded > 0:
            self.status_message.emit(
                f"Note: {n_excluded} rows excluded (label not in selected classes).")

        res = roc_analysis(encoded, score_ser)
        if "error" in res:
            self.status_message.emit(res["error"]); return

        auc_ci = res["auc_ci"]
        ci_str = (f"{auc_ci[0]:.4f} – {auc_ci[1]:.4f}"
                  if not (np.isnan(auc_ci[0]) or np.isnan(auc_ci[1])) else "N/A")

        at_opt = res.get("at_optimal", {})
        rows = [
            ("N (total)",              res["n"]),
            ("N (positive)",           res["n_positive"]),
            ("N (negative)",           res["n_negative"]),
            ("AUC",                    f"{res['auc']:.4f}"),
            ("AUC 95% CI",             ci_str),
            ("Youden's J",             f"{res['youden_j']:.4f}"),
            ("Optimal Threshold",      f"{res['optimal_threshold']:.4f}"),
            ("Sensitivity @ Optimal",  f"{res['optimal_sens']*100:.2f}%"),
            ("Specificity @ Optimal",  f"{res['optimal_spec']*100:.2f}%"),
            ("PPV @ Optimal",          f"{at_opt.get('ppv', np.nan)*100:.2f}%" if at_opt else "N/A"),
            ("NPV @ Optimal",          f"{at_opt.get('npv', np.nan)*100:.2f}%" if at_opt else "N/A"),
            ("Accuracy @ Optimal",     f"{at_opt.get('accuracy', np.nan)*100:.2f}%" if at_opt else "N/A"),
        ]
        self._roc_metrics_table.show_df(pd.DataFrame(rows, columns=["Metric", "Value"]))
        self._roc_curve_table.show_df(res["curve_table"])
        self._plot_roc(res)
        self.status_message.emit(f"ROC analysis done. AUC = {res['auc']:.4f}")

    def _plot_roc(self, res: dict):
        ax = self._roc_plot.get_ax()
        fpr, tpr = res["fpr"], res["tpr"]
        auc_val  = res["auc"]
        ci       = res["auc_ci"]
        opt_fpr  = 1 - res["optimal_spec"]
        opt_tpr  = res["optimal_sens"]

        ci_label = (f" (95% CI: {ci[0]:.3f}–{ci[1]:.3f})" if not np.isnan(ci[0]) else "")
        ax.plot(fpr, tpr, color="#0ea5e9", lw=2, label=f"AUC = {auc_val:.4f}{ci_label}")
        ax.plot([0, 1], [0, 1], color="#475569", lw=1, linestyle="--", label="Chance (AUC=0.5)")
        ax.scatter([opt_fpr], [opt_tpr], color="#f59e0b", s=80, zorder=5,
                   label=f"Optimal (J={res['youden_j']:.3f}, thr={res['optimal_threshold']:.3f})")
        ax.annotate(f"  Sens={opt_tpr*100:.1f}%\n  Spec={res['optimal_spec']*100:.1f}%",
                    xy=(opt_fpr, opt_tpr), color="#f59e0b", fontsize=8)
        ax.fill_between(fpr, tpr, alpha=0.15, color="#0ea5e9")
        ax.set_xlabel("1 − Specificity (FPR)")
        ax.set_ylabel("Sensitivity (TPR)")
        ax.set_title("Receiver Operating Characteristic (ROC) Curve")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#1e293b")
        ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
        self._roc_plot.draw()
