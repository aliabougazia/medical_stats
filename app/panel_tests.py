"""
app/panel_tests.py – Statistical Tests panel.

Supports:
 • Normality tests
 • One-sample T-test
 • Independent T-test / Welch
 • Paired T-test
 • Mann-Whitney U
 • Wilcoxon Signed-Rank
 • Chi-Square / Fisher's Exact
 • McNemar's Test
 • One-Way ANOVA + Tukey HSD
 • Two-Way ANOVA
 • Kruskal-Wallis + post-hoc
 • MANOVA
 • Friedman Test
 • Odds Ratio & Relative Risk
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QListWidget, QAbstractItemView, QGroupBox,
    QSplitter, QTabWidget, QScrollArea, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .core import data_store
from .widgets import PlotWidget, ResultsTable, SectionHeader, Divider
from . import statistics as S


_TESTS = [
    "--- Parametric ---",
    "One-Sample T-Test",
    "Independent T-Test (Welch)",
    "Paired T-Test",
    "One-Way ANOVA",
    "Two-Way ANOVA",
    "MANOVA",
    "--- Non-Parametric ---",
    "Mann-Whitney U Test",
    "Wilcoxon Signed-Rank",
    "Kruskal-Wallis",
    "Friedman Test",
    "--- Categorical ---",
    "Chi-Square / Fisher Exact",
    "McNemar's Test",
    "Odds Ratio & Relative Risk",
    "--- Extra ---",
    "Sample Size: Two Means",
    "Sample Size: Two Proportions",
]


class TestsPanel(QWidget):
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
        root.addWidget(SectionHeader("Statistical Tests"))
        root.addWidget(Divider())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left control panel ────────────────────────────────────────────────
        left = QScrollArea(); left.setWidgetResizable(True); left.setMaximumWidth(330)
        lw   = QWidget()
        llay = QVBoxLayout(lw)
        llay.setContentsMargins(4, 4, 4, 4)
        llay.setSpacing(10)

        grp_test = QGroupBox("Select Test")
        gt_lay   = QVBoxLayout(grp_test)
        self._test_combo = QComboBox()
        self._test_combo.addItems(_TESTS)
        self._test_combo.currentTextChanged.connect(self._on_test_changed)
        gt_lay.addWidget(self._test_combo)
        llay.addWidget(grp_test)

        # Dynamic config area
        self._cfg_stack = QStackedWidget()
        self._cfg_widgets: dict[str, QWidget] = {}
        self._build_config_widgets()
        llay.addWidget(self._cfg_stack)

        run_btn = QPushButton("▶  Run Test")
        run_btn.setObjectName("primary"); run_btn.setMinimumHeight(36)
        run_btn.clicked.connect(self._run)
        llay.addWidget(run_btn)
        llay.addStretch()
        left.setWidget(lw)

        # ── Right results area ────────────────────────────────────────────────
        right = QWidget()
        rlay  = QVBoxLayout(right)
        rlay.setContentsMargins(8, 0, 0, 0)
        rlay.setSpacing(6)

        result_tabs = QTabWidget()
        self._result_table = ResultsTable()
        result_tabs.addTab(self._result_table, "📋  Results")
        self._post_hoc_table = ResultsTable()
        result_tabs.addTab(self._post_hoc_table, "📋  Post-Hoc")
        self._test_plot = PlotWidget(figsize=(7, 4.5))
        result_tabs.addTab(self._test_plot, "📊  Plot")

        rlay.addWidget(result_tabs, stretch=1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    # ── Config widget factory ─────────────────────────────────────────────────

    def _col_combo(self, label: str = "") -> QComboBox:
        cb = QComboBox()
        cb.setProperty("is_col_combo", True)
        return cb

    def _make_two_group(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._tg_outcome = self._col_combo(); fl.addRow("Outcome (numeric):", self._tg_outcome)
        self._tg_group   = self._col_combo(); fl.addRow("Group column (2 groups):", self._tg_group)
        return w

    def _make_paired(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._p_col1 = self._col_combo(); fl.addRow("Variable 1 (before):", self._p_col1)
        self._p_col2 = self._col_combo(); fl.addRow("Variable 2 (after):", self._p_col2)
        return w

    def _make_oneway(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._ow_outcome = self._col_combo(); fl.addRow("Outcome (numeric):", self._ow_outcome)
        self._ow_group   = self._col_combo(); fl.addRow("Group column:", self._ow_group)
        return w

    def _make_twoway(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._tw_outcome = self._col_combo(); fl.addRow("Outcome (numeric):", self._tw_outcome)
        self._tw_f1 = self._col_combo(); fl.addRow("Factor 1:", self._tw_f1)
        self._tw_f2 = self._col_combo(); fl.addRow("Factor 2:", self._tw_f2)
        return w

    def _make_manova(self) -> QWidget:
        w  = QWidget()
        fl = QVBoxLayout(w)
        fl.addWidget(QLabel("Dependent variables (Ctrl+click):"))
        self._manova_dvs = QListWidget()
        self._manova_dvs.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._manova_dvs.setMaximumHeight(120)
        fl.addWidget(self._manova_dvs)
        fl2 = QFormLayout()
        self._manova_factor = self._col_combo(); fl2.addRow("Factor (group):", self._manova_factor)
        fl.addLayout(fl2)
        return w

    def _make_chi(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._chi_c1 = self._col_combo(); fl.addRow("Variable 1:", self._chi_c1)
        self._chi_c2 = self._col_combo(); fl.addRow("Variable 2:", self._chi_c2)
        return w

    def _make_onesample(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._os_col = self._col_combo(); fl.addRow("Variable:", self._os_col)
        self._os_mu  = QDoubleSpinBox(); self._os_mu.setRange(-1e9, 1e9); self._os_mu.setValue(0)
        fl.addRow("Hypothesised mean (μ₀):", self._os_mu)
        return w

    def _make_friedman(self) -> QWidget:
        w  = QWidget()
        fl = QVBoxLayout(w)
        fl.addWidget(QLabel("Select ≥2 columns (conditions):"))
        self._fried_list = QListWidget()
        self._fried_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._fried_list.setMaximumHeight(140)
        fl.addWidget(self._fried_list)
        return w

    def _make_or_rr(self) -> QWidget:
        w   = QWidget()
        fl  = QFormLayout(w)
        self._or_a = QSpinBox(); self._or_a.setRange(0, 999999); self._or_a.setValue(80)
        self._or_b = QSpinBox(); self._or_b.setRange(0, 999999); self._or_b.setValue(40)
        self._or_c = QSpinBox(); self._or_c.setRange(0, 999999); self._or_c.setValue(20)
        self._or_d = QSpinBox(); self._or_d.setRange(0, 999999); self._or_d.setValue(90)
        fl.addRow("Exposed | Cases (a):", self._or_a)
        fl.addRow("Exposed | Controls (b):", self._or_b)
        fl.addRow("Unexposed | Cases (c):", self._or_c)
        fl.addRow("Unexposed | Controls (d):", self._or_d)
        return w

    def _make_ss_means(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._ss_m1  = QDoubleSpinBox(); self._ss_m1.setRange(-1e9, 1e9); self._ss_m1.setValue(50)
        self._ss_m2  = QDoubleSpinBox(); self._ss_m2.setRange(-1e9, 1e9); self._ss_m2.setValue(55)
        self._ss_std = QDoubleSpinBox(); self._ss_std.setRange(0.001, 1e9); self._ss_std.setValue(10)
        self._ss_pow = QDoubleSpinBox(); self._ss_pow.setRange(0.5, 0.99); self._ss_pow.setValue(0.80); self._ss_pow.setSingleStep(0.05)
        self._ss_alp = QDoubleSpinBox(); self._ss_alp.setRange(0.001, 0.2); self._ss_alp.setValue(0.05); self._ss_alp.setSingleStep(0.01)
        fl.addRow("Mean group 1:", self._ss_m1)
        fl.addRow("Mean group 2:", self._ss_m2)
        fl.addRow("Common SD:", self._ss_std)
        fl.addRow("Power:", self._ss_pow)
        fl.addRow("Alpha:", self._ss_alp)
        return w

    def _make_ss_props(self) -> QWidget:
        w  = QWidget()
        fl = QFormLayout(w)
        self._ss_p1  = QDoubleSpinBox(); self._ss_p1.setRange(0.001, 0.999); self._ss_p1.setValue(0.30); self._ss_p1.setSingleStep(0.05)
        self._ss_p2  = QDoubleSpinBox(); self._ss_p2.setRange(0.001, 0.999); self._ss_p2.setValue(0.50); self._ss_p2.setSingleStep(0.05)
        self._ss_p_pow = QDoubleSpinBox(); self._ss_p_pow.setRange(0.5, 0.99); self._ss_p_pow.setValue(0.80); self._ss_p_pow.setSingleStep(0.05)
        self._ss_p_alp = QDoubleSpinBox(); self._ss_p_alp.setRange(0.001, 0.2); self._ss_p_alp.setValue(0.05); self._ss_p_alp.setSingleStep(0.01)
        fl.addRow("Proportion 1:", self._ss_p1)
        fl.addRow("Proportion 2:", self._ss_p2)
        fl.addRow("Power:", self._ss_p_pow)
        fl.addRow("Alpha:", self._ss_p_alp)
        return w

    def _build_config_widgets(self):
        default = QWidget()
        self._add_cfg("default", default)
        self._add_cfg("One-Sample T-Test", self._make_onesample())
        self._add_cfg("Independent T-Test (Welch)", self._make_two_group())
        self._add_cfg("Paired T-Test", self._make_paired())
        self._add_cfg("One-Way ANOVA", self._make_oneway())
        self._add_cfg("Two-Way ANOVA", self._make_twoway())
        self._add_cfg("MANOVA", self._make_manova())
        self._add_cfg("Mann-Whitney U Test", self._make_two_group())
        self._add_cfg("Wilcoxon Signed-Rank", self._make_paired())
        self._add_cfg("Kruskal-Wallis", self._make_oneway())
        self._add_cfg("Friedman Test", self._make_friedman())
        self._add_cfg("Chi-Square / Fisher Exact", self._make_chi())
        self._add_cfg("McNemar's Test", self._make_chi())
        self._add_cfg("Odds Ratio & Relative Risk", self._make_or_rr())
        self._add_cfg("Sample Size: Two Means", self._make_ss_means())
        self._add_cfg("Sample Size: Two Proportions", self._make_ss_props())

    def _add_cfg(self, key: str, w: QWidget):
        self._cfg_widgets[key] = w
        self._cfg_stack.addWidget(w)

    def _on_test_changed(self, text: str):
        w = self._cfg_widgets.get(text, self._cfg_widgets["default"])
        self._cfg_stack.setCurrentWidget(w)

    # ── Data listener ─────────────────────────────────────────────────────────

    def _on_data_change(self):
        df = data_store.df
        cols = list(df.columns) if df is not None else []
        combos = [
            getattr(self, nm, None)
            for nm in ("_tg_outcome", "_tg_group", "_p_col1", "_p_col2",
                       "_ow_outcome", "_ow_group", "_tw_outcome", "_tw_f1", "_tw_f2",
                       "_manova_factor", "_chi_c1", "_chi_c2", "_os_col")
        ]
        for cb in combos:
            if cb is None: continue
            cb.clear(); cb.addItems(cols)
        for lb in (getattr(self, "_manova_dvs", None),
                   getattr(self, "_fried_list", None)):
            if lb is None: continue
            lb.clear(); lb.addItems(cols)

    # ── Run dispatch ──────────────────────────────────────────────────────────

    def _run(self):
        test = self._test_combo.currentText()
        if test.startswith("---"):
            self.status_message.emit("Select a test."); return
        df = data_store.df

        # Dispatch
        if test == "One-Sample T-Test":
            res = S.t_test_one_sample(df[self._os_col.currentText()], mu0=self._os_mu.value())
            self._show_generic(res); self._plot_onesample(df, res)

        elif test == "Independent T-Test (Welch)":
            oc, gc = self._tg_outcome.currentText(), self._tg_group.currentText()
            grps, names = self._split_groups(df, oc, gc)
            if grps is None: return
            g1, g2 = grps; n1, n2 = names
            res = S.t_test_independent(pd.Series(g1), pd.Series(g2))
            res["group1_name"] = n1; res["group2_name"] = n2
            self._show_generic(res); self._plot_two_group(df, oc, gc)

        elif test == "Paired T-Test":
            c1, c2 = self._p_col1.currentText(), self._p_col2.currentText()
            if not df is not None: return
            res = S.t_test_paired(df[c1], df[c2])
            self._show_generic(res); self._plot_paired(df, c1, c2)

        elif test == "One-Way ANOVA":
            oc, gc = self._ow_outcome.currentText(), self._ow_group.currentText()
            grps, names = self._split_groups(df, oc, gc)
            if grps is None: return
            res = S.one_way_anova(*[pd.Series(g) for g in grps], group_names=names)
            self._show_anova(res); self._plot_anova(df, oc, gc)

        elif test == "Two-Way ANOVA":
            res = S.two_way_anova(df, self._tw_outcome.currentText(),
                                   self._tw_f1.currentText(), self._tw_f2.currentText())
            self._show_generic_df(res)

        elif test == "MANOVA":
            dvs = [item.text() for item in self._manova_dvs.selectedItems()]
            if not dvs:
                self.status_message.emit("Select dependent variables."); return
            res = S.manova_test(df, dvs, self._manova_factor.currentText())
            self._show_text(res.get("summary", res.get("error", "")))

        elif test == "Mann-Whitney U Test":
            oc, gc = self._tg_outcome.currentText(), self._tg_group.currentText()
            grps, names = self._split_groups(df, oc, gc)
            if grps is None: return
            g1, g2 = grps; n1, n2 = names
            res = S.mann_whitney(pd.Series(g1), pd.Series(g2))
            res["group1_name"] = n1; res["group2_name"] = n2
            self._show_generic(res); self._plot_two_group(df, oc, gc)

        elif test == "Wilcoxon Signed-Rank":
            c1, c2 = self._p_col1.currentText(), self._p_col2.currentText()
            res = S.wilcoxon_signed_rank(df[c1], df[c2])
            self._show_generic(res)

        elif test == "Kruskal-Wallis":
            oc, gc = self._ow_outcome.currentText(), self._ow_group.currentText()
            grps, names = self._split_groups(df, oc, gc)
            if grps is None: return
            res = S.kruskal_wallis(*[pd.Series(g) for g in grps], group_names=names)
            self._show_generic(res); self._plot_anova(df, oc, gc)

        elif test == "Friedman Test":
            cols = [item.text() for item in self._fried_list.selectedItems()]
            if len(cols) < 2:
                self.status_message.emit("Select ≥2 columns."); return
            res = S.friedman_test(*[df[c] for c in cols], group_names=cols)
            self._show_generic(res)

        elif test == "Chi-Square / Fisher Exact":
            c1, c2 = self._chi_c1.currentText(), self._chi_c2.currentText()
            res = S.chi_square(df[c1], df[c2])
            self._show_chi(res, df, c1, c2)

        elif test == "McNemar's Test":
            c1, c2 = self._chi_c1.currentText(), self._chi_c2.currentText()
            ct = pd.crosstab(df[c1], df[c2]).values
            if ct.shape != (2, 2):
                self.status_message.emit("McNemar requires a 2×2 table."); return
            res = S.mcnemar(ct)
            self._show_generic(res)

        elif test == "Odds Ratio & Relative Risk":
            res = S.odds_ratio_rr(self._or_a.value(), self._or_b.value(),
                                   self._or_c.value(), self._or_d.value())
            self._show_generic(res)

        elif test == "Sample Size: Two Means":
            res = S.sample_size_means(self._ss_m1.value(), self._ss_m2.value(),
                                       self._ss_std.value(), self._ss_alp.value(),
                                       self._ss_pow.value())
            self._show_generic(res)

        elif test == "Sample Size: Two Proportions":
            res = S.sample_size_proportions(self._ss_p1.value(), self._ss_p2.value(),
                                             self._ss_p_alp.value(), self._ss_p_pow.value())
            self._show_generic(res)

        p = res.get("p_value")
        sig_str = ""
        if p is not None and not (isinstance(p, float) and np.isnan(p)):
            sig_str = f"  |  p = {p:.4f}  {'✓ Significant' if p < 0.05 else '✗ Not significant'}"
        self.status_message.emit(f"{test} completed.{sig_str}")

    # ── Helper: split DataFrame by group ─────────────────────────────────────

    def _split_groups(self, df, outcome_col, group_col):
        if df is None:
            self.status_message.emit("No data loaded."); return None, None
        ugroups = df[group_col].dropna().unique()
        if len(ugroups) < 2:
            self.status_message.emit("Group column must have ≥2 unique values."); return None, None
        grps  = [df[df[group_col] == g][outcome_col].dropna().values for g in ugroups]
        names = [str(g) for g in ugroups]
        return grps, names

    # ── Display helpers ───────────────────────────────────────────────────────

    def _show_generic(self, res: dict):
        """Display a flat key-value dict as a two-column table."""
        rows = []
        for k, v in res.items():
            if isinstance(v, (pd.DataFrame, np.ndarray, list, tuple)):
                continue
            rows.append({"Metric": str(k), "Value": v})
        df_out = pd.DataFrame(rows)
        self._result_table.show_df(df_out, p_cols=["Value"
                                                    if any("p_value" in str(r.get("Metric", "")).lower() for r in rows) else "___"])
        p_rows = [r for r in rows if "p" in str(r.get("Metric", "")).lower()]
        self._result_table.show_df(df_out)
        self._post_hoc_table._table.clear()
        self._post_hoc_table._table.setRowCount(0)

    def _show_generic_df(self, res: dict):
        tbl = res.get("table")
        if tbl is not None and isinstance(tbl, pd.DataFrame):
            self._result_table.show_df(tbl.reset_index(), p_cols=["PR(>F)"])
        elif "error" in res:
            self._show_text(res["error"])

    def _show_anova(self, res: dict):
        self._show_generic(res)
        tukey = res.get("tukey_table")
        if tukey is not None and isinstance(tukey, pd.DataFrame):
            self._post_hoc_table.show_df(tukey, p_cols=["p-adj"])

    def _show_chi(self, res: dict, df, c1, c2):
        ct = res.get("contingency_table")
        if ct is not None:
            ct_reset = ct.reset_index()
            self._result_table.show_df(ct_reset)
        rows = []
        for k in ("statistic", "p_value", "significant", "df", "n", "cramers_v",
                  "min_expected", "fisher_exact_p", "fisher_odds_ratio"):
            if k in res:
                rows.append({"Metric": k, "Value": res[k]})
        if rows:
            self._post_hoc_table.show_df(pd.DataFrame(rows))
        self._plot_chi(df, c1, c2)

    def _show_text(self, text: str):
        rows = [{"Output": text}]
        self._result_table.show_df(pd.DataFrame(rows))

    # ── Plots ─────────────────────────────────────────────────────────────────

    _PAL = ["#0ea5e9", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444", "#ec4899"]

    def _plot_two_group(self, df, outcome, group):
        ax = self._test_plot.get_ax()
        groups = df[group].dropna().unique()
        positions = range(len(groups))
        data = [df[df[group] == g][outcome].dropna().values for g in groups]
        vp = ax.violinplot(data, positions=list(positions), showmedians=True)
        for i, pc in enumerate(vp["bodies"]):
            pc.set_facecolor(self._PAL[i % len(self._PAL)]); pc.set_alpha(0.7)
        vp["cmedians"].set_color("#f59e0b")
        ax.set_xticks(list(positions)); ax.set_xticklabels([str(g) for g in groups])
        ax.set_ylabel(outcome); ax.set_title(f"{outcome} by {group}")
        self._test_plot.draw()

    def _plot_onesample(self, df, res):
        ax = self._test_plot.get_ax()
        s  = df[self._os_col.currentText()].dropna()
        ax.hist(s, bins="auto", color="#0ea5e9", edgecolor="#334155", alpha=0.8)
        ax.axvline(res["mean"],  color="#22c55e", lw=2, label=f"Mean={res['mean']:.3g}")
        ax.axvline(res["hypothesized_mean"], color="#ef4444", lw=2, linestyle="--",
                   label=f"μ₀={res['hypothesized_mean']:.3g}")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        ax.set_title(f"One-Sample Distribution  (p={res['p_value']:.4f})")
        self._test_plot.draw()

    def _plot_paired(self, df, c1, c2):
        ax = self._test_plot.get_ax()
        d1 = df[c1].dropna().values; d2 = df[c2].dropna().values
        n  = min(len(d1), len(d2)); d1, d2 = d1[:n], d2[:n]
        for i in range(min(n, 80)):
            ax.plot([0, 1], [d1[i], d2[i]], color="#334155", lw=0.8, alpha=0.5)
        ax.scatter([0]*n, d1, color="#0ea5e9", s=25, zorder=3, label=c1)
        ax.scatter([1]*n, d2, color="#8b5cf6", s=25, zorder=3, label=c2)
        ax.plot([0, 1], [np.mean(d1), np.mean(d2)], color="#f59e0b", lw=2, zorder=4)
        ax.set_xticks([0, 1]); ax.set_xticklabels([c1, c2])
        ax.set_title("Paired Observations")
        ax.legend(fontsize=8, labelcolor="#f1f5f9", facecolor="#334155")
        self._test_plot.draw()

    def _plot_anova(self, df, outcome, group):
        self._plot_two_group(df, outcome, group)

    def _plot_chi(self, df, c1, c2):
        ax = self._test_plot.get_ax()
        ct = pd.crosstab(df[c1], df[c2])
        ct.plot(kind="bar", ax=ax, color=self._PAL[:len(ct.columns)],
                edgecolor="#334155", alpha=0.85)
        ax.set_xlabel(str(c1)); ax.set_ylabel("Count")
        ax.set_title(f"Contingency: {c1} vs {c2}")
        ax.legend(title=str(c2), fontsize=8, labelcolor="#f1f5f9", facecolor="#334155",
                  title_fontsize=8)
        for p in ax.patches:
            ax.text(p.get_x() + p.get_width()/2, p.get_height() + 0.5,
                    str(int(p.get_height())), ha="center", fontsize=7, color="#94a3b8")
        self._test_plot.draw()
