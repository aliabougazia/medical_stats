"""
app/statistics.py – All statistical computation functions.

Every function returns a plain dict suitable for display/export.
No Qt imports here – pure Python/NumPy/SciPy/statsmodels.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _arr(x) -> np.ndarray:
    """Convert Series/list to clean float array (dropping NaN)."""
    if hasattr(x, "dropna"):
        x = x.dropna()
    a = np.asarray(x, dtype=float)
    return a[~np.isnan(a)]


def _wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion."""
    if n == 0:
        return np.nan, np.nan
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return float(max(0, centre - margin)), float(min(1, centre + margin))


def _check_normal(a: np.ndarray) -> bool:
    if len(a) < 3:
        return False
    try:
        _, p = stats.shapiro(a)
        return bool(p > 0.05)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# DESCRIPTIVE STATISTICS
# ═══════════════════════════════════════════════════════════════

def quantitative_stats(series, ci: float = 0.95) -> dict:
    """Full descriptive stats for a continuous variable."""
    s = _arr(series)
    n = len(s)
    if n == 0:
        return {"error": "No valid data."}
    mean = float(np.mean(s))
    std  = float(np.std(s, ddof=1)) if n > 1 else 0.0
    sem  = std / np.sqrt(n) if n > 1 else 0.0
    t_c  = stats.t.ppf((1 + ci) / 2, df=max(n - 1, 1))
    ci_l, ci_u = mean - t_c * sem, mean + t_c * sem

    # Normality
    sw_s, sw_p = (np.nan, np.nan)
    if n >= 3:
        try:
            sw_s, sw_p = stats.shapiro(s)
        except Exception:
            pass

    # D'Agostino-Pearson (n ≥ 8)
    dp_s, dp_p = (np.nan, np.nan)
    if n >= 8:
        try:
            dp_s, dp_p = stats.normaltest(s)
        except Exception:
            pass

    return {
        "n":             n,
        "missing":       int(pd.Series(series).isna().sum() if hasattr(series, "isna") else 0),
        "mean":          mean,
        "std":           std,
        "sem":           sem,
        "min":           float(np.min(s)),
        "q1":            float(np.percentile(s, 25)),
        "median":        float(np.median(s)),
        "q3":            float(np.percentile(s, 75)),
        "max":           float(np.max(s)),
        "iqr":           float(np.percentile(s, 75) - np.percentile(s, 25)),
        "range":         float(np.max(s) - np.min(s)),
        "ci_lower":      float(ci_l),
        "ci_upper":      float(ci_u),
        "ci_level":      ci,
        "skewness":      float(stats.skew(s)),
        "kurtosis":      float(stats.kurtosis(s)),
        "shapiro_stat":  float(sw_s) if not np.isnan(sw_s) else None,
        "shapiro_p":     float(sw_p) if not np.isnan(sw_p) else None,
        "dagostino_stat": float(dp_s) if not np.isnan(dp_s) else None,
        "dagostino_p":   float(dp_p) if not np.isnan(dp_p) else None,
        "is_normal":     bool(sw_p > 0.05) if not (isinstance(sw_p, float) and np.isnan(sw_p)) else None,
    }


def categorical_stats(series) -> dict:
    """Frequency table for a categorical variable."""
    s = pd.Series(series).dropna()
    n = len(s)
    if n == 0:
        return {"error": "No valid data."}
    counts = s.value_counts()
    table = pd.DataFrame({
        "Category":    counts.index.tolist(),
        "n":           counts.values.tolist(),
        "Percent (%)": (counts.values / n * 100).round(2).tolist(),
    })
    return {
        "n":            n,
        "missing":      int(pd.Series(series).isna().sum() if hasattr(series, "isna") else 0),
        "n_categories": int(len(counts)),
        "mode":         str(counts.index[0]),
        "mode_n":       int(counts.iloc[0]),
        "table":        table,
    }


def normality_tests(series) -> dict:
    """Battery of normality tests."""
    s = _arr(series)
    n = len(s)
    results: dict[str, dict] = {}

    if n >= 3:
        try:
            w, p = stats.shapiro(s)
            results["Shapiro-Wilk"] = {"statistic": float(w), "p_value": float(p), "normal": p > 0.05}
        except Exception:
            pass
    if n >= 20:
        try:
            d, p = stats.kstest(s, "norm", args=(np.mean(s), np.std(s)))
            results["Kolmogorov-Smirnov"] = {"statistic": float(d), "p_value": float(p), "normal": p > 0.05}
        except Exception:
            pass
    if n >= 8:
        try:
            k2, p = stats.normaltest(s)
            results["D'Agostino-Pearson"] = {"statistic": float(k2), "p_value": float(p), "normal": p > 0.05}
        except Exception:
            pass
    if n >= 7:
        try:
            res = stats.anderson(s, "norm")
            crit = res.critical_values[2]  # 5 %
            results["Anderson-Darling"] = {
                "statistic": float(res.statistic),
                "critical_5pct": float(crit),
                "normal": res.statistic < crit,
            }
        except Exception:
            pass
    return {"n": n, "tests": results}


# ═══════════════════════════════════════════════════════════════
# DIAGNOSTIC METRICS
# ═══════════════════════════════════════════════════════════════

def diagnostic_metrics(tp: int, fp: int, fn: int, tn: int, ci: float = 0.95) -> dict:
    """2×2 contingency table → full diagnostic performance metrics."""
    total = tp + fp + fn + tn
    if total == 0:
        return {"error": "All cells are zero."}

    sens = tp / (tp + fn)      if (tp + fn) > 0 else np.nan
    spec = tn / (tn + fp)      if (tn + fp) > 0 else np.nan
    ppv  = tp / (tp + fp)      if (tp + fp) > 0 else np.nan
    npv  = tn / (tn + fn)      if (tn + fn) > 0 else np.nan
    acc  = (tp + tn) / total
    f1   = 2*tp / (2*tp+fp+fn) if (2*tp+fp+fn) > 0 else np.nan
    lr_p = sens / (1-spec)     if (not np.isnan(spec) and spec < 1.0) else np.nan
    lr_n = (1-sens) / spec     if (not np.isnan(spec) and spec > 0) else np.nan
    dor  = lr_p / lr_n         if (not np.isnan(lr_p) and not np.isnan(lr_n) and lr_n > 0) else np.nan
    prev = (tp + fn) / total

    z = stats.norm.ppf((1 + ci) / 2)

    def wci(val, n_d):
        if np.isnan(val) or n_d == 0:
            return (np.nan, np.nan)
        return _wilson_ci(val, n_d, z)

    return {
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
        "total": total,
        "sensitivity":      sens,   "sensitivity_ci":  wci(sens, tp+fn),
        "specificity":      spec,   "specificity_ci":  wci(spec, tn+fp),
        "ppv":              ppv,    "ppv_ci":          wci(ppv,  tp+fp),
        "npv":              npv,    "npv_ci":          wci(npv,  tn+fn),
        "accuracy":         acc,    "accuracy_ci":     wci(acc,  total),
        "f1_score":         f1,
        "lr_positive":      lr_p,
        "lr_negative":      lr_n,
        "diagnostic_odds_ratio": dor,
        "prevalence":       prev,
        "ci_level":         ci,
    }


# ═══════════════════════════════════════════════════════════════
# ROC CURVE
# ═══════════════════════════════════════════════════════════════

def roc_analysis(y_true, y_score, n_bootstrap: int = 1000, ci: float = 0.95) -> dict:
    """ROC curve, AUC with bootstrap CI, Youden's index, optimal cutpoint."""
    from sklearn.metrics import roc_curve, auc, roc_auc_score

    yt = np.asarray(y_true, dtype=float)
    ys = np.asarray(y_score, dtype=float)
    mask = ~(np.isnan(yt) | np.isnan(ys))
    yt, ys = yt[mask], ys[mask]
    n = len(yt)

    if n < 5 or len(np.unique(yt)) < 2:
        return {"error": "Need ≥5 observations with both classes present."}

    fpr, tpr, thr = roc_curve(yt, ys)
    auc_val = float(auc(fpr, tpr))

    # Youden's J
    j = tpr - fpr
    idx = int(np.argmax(j))
    opt_thr  = float(thr[idx])
    opt_sens = float(tpr[idx])
    opt_spec = float(1 - fpr[idx])
    youden_j = float(j[idx])

    # Bootstrap CI
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(n_bootstrap):
        i = rng.choice(n, n, replace=True)
        if len(np.unique(yt[i])) < 2:
            continue
        try:
            boot.append(roc_auc_score(yt[i], ys[i]))
        except Exception:
            pass
    alpha = (1 - ci) / 2
    auc_ci = (
        (float(np.percentile(boot, alpha * 100)), float(np.percentile(boot, (1 - alpha) * 100)))
        if len(boot) >= 10 else (np.nan, np.nan)
    )

    curve_table = pd.DataFrame({
        "Threshold":   np.round(thr, 6),
        "Sensitivity": np.round(tpr, 4),
        "Specificity": np.round(1 - fpr, 4),
        "Youden J":    np.round(j, 4),
    })

    # Diagnostic metrics at optimal threshold
    y_pred = (ys >= opt_thr).astype(int)
    tp = int(np.sum((yt == 1) & (y_pred == 1)))
    fp = int(np.sum((yt == 0) & (y_pred == 1)))
    fn = int(np.sum((yt == 1) & (y_pred == 0)))
    tn = int(np.sum((yt == 0) & (y_pred == 0)))

    return {
        "fpr":               fpr,
        "tpr":               tpr,
        "thresholds":        thr,
        "auc":               auc_val,
        "auc_ci":            auc_ci,
        "ci_level":          ci,
        "optimal_threshold": opt_thr,
        "optimal_sens":      opt_sens,
        "optimal_spec":      opt_spec,
        "youden_j":          youden_j,
        "curve_table":       curve_table,
        "n":                 n,
        "n_positive":        int(np.sum(yt == 1)),
        "n_negative":        int(np.sum(yt == 0)),
        "at_optimal": diagnostic_metrics(tp, fp, fn, tn),
    }


# ═══════════════════════════════════════════════════════════════
# STATISTICAL TESTS
# ═══════════════════════════════════════════════════════════════

def t_test_one_sample(series, mu0: float = 0, ci: float = 0.95) -> dict:
    s = _arr(series)
    n = len(s)
    if n < 2:
        return {"error": "Need ≥2 observations."}
    t, p = stats.ttest_1samp(s, popmean=mu0)
    mean, std = float(np.mean(s)), float(np.std(s, ddof=1))
    sem = std / np.sqrt(n)
    tc  = stats.t.ppf((1 + ci) / 2, df=n - 1)
    return {
        "test": "One-Sample T-Test",
        "statistic": float(t), "p_value": float(p), "significant": p < 0.05,
        "df": n - 1, "n": n,
        "mean": mean, "std": std, "sem": sem, "hypothesized_mean": mu0,
        "mean_diff": mean - mu0,
        "ci": (mean - tc * sem, mean + tc * sem),
        "cohens_d": (mean - mu0) / std if std > 0 else np.nan,
        "is_normal": _check_normal(s),
    }


def t_test_independent(g1, g2, ci: float = 0.95) -> dict:
    a, b = _arr(g1), _arr(g2)
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return {"error": "Each group needs ≥2 observations."}

    lev_s, lev_p = stats.levene(a, b)
    equal_var = bool(lev_p > 0.05)
    t, p = stats.ttest_ind(a, b, equal_var=equal_var)

    m1, m2 = float(np.mean(a)), float(np.mean(b))
    s1, s2 = float(np.std(a, ddof=1)), float(np.std(b, ddof=1))
    pooled = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    d = (m1 - m2) / pooled if pooled > 0 else np.nan

    diff = m1 - m2
    if equal_var:
        se = pooled * np.sqrt(1/n1 + 1/n2)
        df = n1 + n2 - 2
    else:
        se = np.sqrt(s1**2/n1 + s2**2/n2)
        df = (s1**2/n1 + s2**2/n2)**2 / ((s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1))
    tc = stats.t.ppf((1 + ci) / 2, df=df)

    return {
        "test":       "Welch's T-Test" if not equal_var else "Independent Samples T-Test",
        "statistic":  float(t),  "p_value": float(p), "significant": p < 0.05,
        "df": float(df),
        "n1": n1, "mean1": m1, "std1": s1,
        "n2": n2, "mean2": m2, "std2": s2,
        "mean_diff": diff, "ci_diff": (diff - tc*se, diff + tc*se), "ci_level": ci,
        "cohens_d": d,
        "levene_stat": float(lev_s), "levene_p": float(lev_p), "equal_variances": equal_var,
        "normal1": _check_normal(a), "normal2": _check_normal(b),
    }


def t_test_paired(s1, s2, ci: float = 0.95) -> dict:
    a, b = _arr(s1), _arr(s2)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < 2:
        return {"error": "Need ≥2 paired observations."}
    t, p = stats.ttest_rel(a, b)
    diff = a - b
    md = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    se = sd / np.sqrt(n)
    tc = stats.t.ppf((1 + ci) / 2, df=n - 1)
    return {
        "test": "Paired Samples T-Test",
        "statistic": float(t), "p_value": float(p), "significant": p < 0.05,
        "df": n - 1, "n": n,
        "mean1": float(np.mean(a)), "std1": float(np.std(a, ddof=1)),
        "mean2": float(np.mean(b)), "std2": float(np.std(b, ddof=1)),
        "mean_diff": md, "std_diff": sd,
        "ci_diff": (md - tc*se, md + tc*se), "ci_level": ci,
        "cohens_d": md / sd if sd > 0 else np.nan,
        "is_normal_diff": _check_normal(diff),
    }


def mann_whitney(g1, g2) -> dict:
    a, b = _arr(g1), _arr(g2)
    if len(a) < 1 or len(b) < 1:
        return {"error": "Each group needs ≥1 observation."}
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    r = 1 - 2*u / (len(a)*len(b))
    return {
        "test": "Mann-Whitney U Test",
        "statistic": float(u), "p_value": float(p), "significant": p < 0.05,
        "n1": len(a), "median1": float(np.median(a)),
        "q1_1": float(np.percentile(a, 25)), "q3_1": float(np.percentile(a, 75)),
        "n2": len(b), "median2": float(np.median(b)),
        "q1_2": float(np.percentile(b, 25)), "q3_2": float(np.percentile(b, 75)),
        "rank_biserial_r": float(r),
    }


def wilcoxon_signed_rank(s1, s2) -> dict:
    a, b = _arr(s1), _arr(s2)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < 2:
        return {"error": "Need ≥2 paired observations."}
    try:
        w, p = stats.wilcoxon(a, b)
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "test": "Wilcoxon Signed-Rank Test",
        "statistic": float(w), "p_value": float(p), "significant": p < 0.05,
        "n": n,
        "median1": float(np.median(a)), "median2": float(np.median(b)),
    }


def chi_square(s1, s2) -> dict:
    ct = pd.crosstab(pd.Series(s1), pd.Series(s2))
    chi2, p, df, exp = stats.chi2_contingency(ct)
    n = int(ct.values.sum())
    r, k = ct.shape
    phi2  = chi2 / n
    cv    = float(np.sqrt(phi2 / min(k-1, r-1))) if min(k-1, r-1) > 0 else np.nan
    result = {
        "test": "Chi-Square Test of Independence",
        "statistic": float(chi2), "p_value": float(p), "significant": p < 0.05,
        "df": int(df), "n": n, "cramers_v": cv,
        "min_expected": float(exp.min()),
        "contingency_table": ct,
        "expected_table": pd.DataFrame(np.round(exp, 2), index=ct.index, columns=ct.columns),
    }
    if ct.shape == (2, 2):
        or_v, fp = stats.fisher_exact(ct.values)
        result["fisher_exact_p"]   = float(fp)
        result["fisher_odds_ratio"] = float(or_v)
    return result


def mcnemar(table: np.ndarray) -> dict:
    from statsmodels.stats.contingency_tables import mcnemar as sm_mcn
    r = sm_mcn(np.asarray(table, dtype=int), exact=True)
    return {
        "test": "McNemar's Test",
        "statistic": float(r.statistic), "p_value": float(r.pvalue), "significant": r.pvalue < 0.05,
    }


def one_way_anova(*groups, group_names=None) -> dict:
    grps = [_arr(g) for g in groups]
    k = len(grps)
    if k < 2:
        return {"error": "Need ≥2 groups."}
    f, p = stats.f_oneway(*grps)
    all_d = np.concatenate(grps)
    gm = np.mean(all_d)
    ss_b = sum(len(g) * (np.mean(g) - gm)**2 for g in grps)
    ss_t = sum((x - gm)**2 for x in all_d)
    n_t = len(all_d)
    df_b, df_w = k - 1, n_t - k
    ms_w = (ss_t - ss_b) / df_w if df_w > 0 else np.nan
    eta   = ss_b / ss_t if ss_t > 0 else np.nan
    omega = (ss_b - df_b * ms_w) / (ss_t + ms_w) if ms_w else np.nan
    names = group_names or [f"Group {i+1}" for i in range(k)]
    sums = [{"group": nm, "n": len(g), "mean": float(np.mean(g)),
             "std": float(np.std(g, ddof=1)), "median": float(np.median(g))}
            for nm, g in zip(names, grps)]

    res = {
        "test": "One-Way ANOVA",
        "statistic": float(f), "p_value": float(p), "significant": p < 0.05,
        "df_between": df_b, "df_within": df_w, "n_total": n_t, "k_groups": k,
        "eta_squared": float(eta), "omega_squared": float(omega),
        "group_summaries": sums,
    }
    if p < 0.05 and k > 2:
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            vals   = np.concatenate(grps)
            labels = np.concatenate([[nm]*len(g) for nm, g in zip(names, grps)])
            tk     = pairwise_tukeyhsd(vals, labels)
            res["tukey_table"] = pd.DataFrame(
                tk._results_table.data[1:], columns=tk._results_table.data[0])
        except Exception as exc:
            res["tukey_error"] = str(exc)
    return res


def kruskal_wallis(*groups, group_names=None) -> dict:
    grps  = [_arr(g) for g in groups]
    k     = len(grps)
    h, p  = stats.kruskal(*grps)
    n_t   = sum(len(g) for g in grps)
    eps   = float((h - k + 1) / (n_t - k)) if n_t > k else np.nan
    names = group_names or [f"Group {i+1}" for i in range(k)]
    sums  = [{"group": nm, "n": len(g), "median": float(np.median(g)),
              "q1": float(np.percentile(g, 25)), "q3": float(np.percentile(g, 75))}
             for nm, g in zip(names, grps)]
    return {
        "test": "Kruskal-Wallis H Test",
        "statistic": float(h), "p_value": float(p), "significant": p < 0.05,
        "df": k - 1, "k_groups": k, "n_total": n_t,
        "epsilon_squared": eps, "group_summaries": sums,
    }


def friedman_test(*groups, group_names=None) -> dict:
    grps = [_arr(g) for g in groups]
    n    = min(len(g) for g in grps)
    grps = [g[:n] for g in grps]
    chi2, p = stats.friedmanchisquare(*grps)
    return {
        "test": "Friedman Test",
        "statistic": float(chi2), "p_value": float(p), "significant": p < 0.05,
        "df": len(grps) - 1, "n": n, "k_conditions": len(grps),
    }


def two_way_anova(df: pd.DataFrame, outcome: str, factor1: str, factor2: str) -> dict:
    """Two-way ANOVA using statsmodels."""
    import statsmodels.formula.api as smf
    formula = f"Q('{outcome}') ~ C(Q('{factor1}')) * C(Q('{factor2}'))"
    try:
        from statsmodels.stats.anova import anova_lm
        model = smf.ols(formula, data=df.dropna(subset=[outcome, factor1, factor2])).fit()
        table = anova_lm(model, typ=2)
        return {"test": "Two-Way ANOVA", "table": table, "summary": model.summary().as_text()}
    except Exception as exc:
        return {"error": str(exc)}


def manova_test(df: pd.DataFrame, outcomes: list[str], factor: str) -> dict:
    """MANOVA."""
    try:
        from statsmodels.multivariate.manova import MANOVA
        dv_str = " + ".join([f"Q('{c}')" for c in outcomes])
        formula = f"{dv_str} ~ C(Q('{factor}'))"
        mv = MANOVA.from_formula(formula, data=df.dropna(subset=outcomes + [factor]))
        res = mv.mv_test()
        return {"test": "MANOVA", "summary": str(res)}
    except Exception as exc:
        return {"error": str(exc)}


# ═══════════════════════════════════════════════════════════════
# REGRESSION
# ═══════════════════════════════════════════════════════════════

def _align(x_df: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, np.ndarray]:
    idx = x_df.dropna().index.intersection(y.dropna().index)
    return x_df.loc[idx], y.loc[idx].values


def simple_linear_regression(x: pd.Series, y: pd.Series) -> dict:
    import statsmodels.api as sm
    xv, yv = _arr(x), _arr(y)
    n = min(len(xv), len(yv))
    xv, yv = xv[:n], yv[:n]
    mask = ~(np.isnan(xv) | np.isnan(yv))
    xv, yv = xv[mask], yv[mask]
    if len(xv) < 3:
        return {"error": "Need ≥3 observations."}

    X = sm.add_constant(xv)
    m = sm.OLS(yv, X).fit()
    r, rp = stats.pearsonr(xv, yv)
    ci_df = m.conf_int()
    params_tbl = pd.DataFrame({
        "": ["Intercept", "Slope"],
        "Coeff": [m.params[0], m.params[1]],
        "SE":    [m.bse[0], m.bse[1]],
        "t":     [m.tvalues[0], m.tvalues[1]],
        "p":     [m.pvalues[0], m.pvalues[1]],
        "CI low":  [ci_df.iloc[0, 0], ci_df.iloc[1, 0]],
        "CI high": [ci_df.iloc[0, 1], ci_df.iloc[1, 1]],
    })
    return {
        "test": "Simple Linear Regression",
        "n": len(xv), "r": float(r), "r_p": float(rp),
        "r_squared": float(m.rsquared), "adj_r_squared": float(m.rsquared_adj),
        "intercept": float(m.params[0]), "slope": float(m.params[1]),
        "f_stat": float(m.fvalue), "f_p": float(m.f_pvalue),
        "aic": float(m.aic), "bic": float(m.bic),
        "params_table": params_tbl,
        "residuals": m.resid, "fitted": m.fittedvalues,
        "x_vals": xv, "y_vals": yv,
    }


def multiple_linear_regression(X_df: pd.DataFrame, y: pd.Series) -> dict:
    import statsmodels.api as sm
    Xc, yv = _align(X_df, y)
    if len(yv) < X_df.shape[1] + 2:
        return {"error": "Too few observations for the number of predictors."}
    Xm = sm.add_constant(Xc)
    m  = sm.OLS(yv, Xm).fit()
    ci = m.conf_int()
    params_tbl = pd.DataFrame({
        "Variable": list(Xm.columns),
        "Coeff":    list(m.params),
        "SE":       list(m.bse),
        "t":        list(m.tvalues),
        "p":        list(m.pvalues),
        "CI Low":   list(ci.iloc[:, 0]),
        "CI High":  list(ci.iloc[:, 1]),
    })
    # VIF
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        vif = pd.DataFrame({
            "Variable": Xm.columns,
            "VIF": [variance_inflation_factor(Xm.values, i) for i in range(Xm.shape[1])],
        })
    except Exception:
        vif = None
    return {
        "test": "Multiple Linear Regression",
        "n": len(yv), "k": X_df.shape[1],
        "r_squared": float(m.rsquared), "adj_r_squared": float(m.rsquared_adj),
        "f_stat": float(m.fvalue), "f_p": float(m.f_pvalue),
        "aic": float(m.aic), "bic": float(m.bic),
        "params_table": params_tbl, "vif_table": vif,
        "residuals": m.resid, "fitted": m.fittedvalues,
    }


def logistic_regression(X_df: pd.DataFrame, y: pd.Series) -> dict:
    import statsmodels.api as sm
    from sklearn.metrics import roc_auc_score, confusion_matrix
    Xc, yv = _align(X_df, y)
    if len(np.unique(yv)) != 2:
        return {"error": "Outcome must be binary (2 unique values)."}
    Xm = sm.add_constant(Xc)
    try:
        m = sm.Logit(yv, Xm).fit(disp=0, maxiter=200)
    except Exception as exc:
        return {"error": str(exc)}
    ci = m.conf_int()
    params_tbl = pd.DataFrame({
        "Variable": list(Xm.columns),
        "β":        list(m.params),
        "SE":       list(m.bse),
        "z":        list(m.tvalues),
        "p":        list(m.pvalues),
        "OR":       list(np.exp(m.params)),
        "OR CI Low":  list(np.exp(ci.iloc[:, 0])),
        "OR CI High": list(np.exp(ci.iloc[:, 1])),
    })
    proba = m.predict()
    try:
        auc_v = float(roc_auc_score(yv, proba))
    except Exception:
        auc_v = np.nan
    pred  = (proba >= 0.5).astype(int)
    cm    = confusion_matrix(yv, pred)
    return {
        "test": "Binary Logistic Regression",
        "n": len(yv), "k": X_df.shape[1],
        "params_table": params_tbl,
        "log_likelihood": float(m.llf),
        "aic": float(m.aic), "bic": float(m.bic),
        "pseudo_r2_mcfadden": float(m.prsquared),
        "auc": auc_v,
        "confusion_matrix": cm,
        "predicted_proba": proba, "y_true": yv,
    }


def poisson_regression(X_df: pd.DataFrame, y: pd.Series) -> dict:
    import statsmodels.api as sm
    Xc, yv = _align(X_df, y)
    Xm = sm.add_constant(Xc)
    try:
        m = sm.GLM(yv, Xm, family=sm.families.Poisson()).fit()
    except Exception as exc:
        return {"error": str(exc)}
    ci = m.conf_int()
    params_tbl = pd.DataFrame({
        "Variable": list(Xm.columns),
        "β":    list(m.params),
        "SE":   list(m.bse),
        "z":    list(m.tvalues),
        "p":    list(m.pvalues),
        "IRR":  list(np.exp(m.params)),
        "IRR CI Low":  list(np.exp(ci.iloc[:, 0])),
        "IRR CI High": list(np.exp(ci.iloc[:, 1])),
    })
    return {
        "test": "Poisson Regression", "n": len(yv),
        "params_table": params_tbl,
        "aic": float(m.aic), "bic": float(m.bic), "deviance": float(m.deviance),
    }


# ═══════════════════════════════════════════════════════════════
# RELIABILITY & AGREEMENT
# ═══════════════════════════════════════════════════════════════

def cohens_kappa(r1, r2) -> dict:
    from sklearn.metrics import cohen_kappa_score
    a, b = _arr(r1).astype(int), _arr(r2).astype(int)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    k = float(cohen_kappa_score(a, b))
    try:
        wk = float(cohen_kappa_score(a, b, weights="quadratic"))
    except Exception:
        wk = np.nan
    agree = float(np.mean(a == b))
    interp = ("Almost Perfect" if k >= 0.8 else
              "Substantial"    if k >= 0.6 else
              "Moderate"       if k >= 0.4 else
              "Fair"           if k >= 0.2 else
              "Slight"         if k >= 0   else "Poor (< chance)")
    return {
        "kappa": k, "weighted_kappa": wk,
        "observed_agreement": agree,
        "interpretation": interp, "n": n,
    }


def icc_analysis(df_wide: pd.DataFrame) -> dict:
    """ICC from wide-format DataFrame (columns = raters, rows = subjects)."""
    try:
        import pingouin as pg
        long = df_wide.reset_index(drop=True).copy()
        long.index.name = "subject"
        long = long.reset_index().melt(id_vars="subject", var_name="rater", value_name="score")
        long = long.dropna(subset=["score"])
        res = pg.intraclass_corr(data=long, targets="subject", raters="rater", ratings="score")
        return {"icc_table": res, "n_subjects": len(df_wide), "n_raters": df_wide.shape[1]}
    except ImportError:
        pass
    # Fallback (two-way random, single measures)
    data = df_wide.dropna().values
    n, k = data.shape
    gm   = np.mean(data)
    rm   = np.mean(data, axis=1)
    cm   = np.mean(data, axis=0)
    ss_r = k * np.sum((rm - gm)**2)
    ss_c = n * np.sum((cm - gm)**2)
    ss_t = np.sum((data - gm)**2)
    ss_e = ss_t - ss_r - ss_c
    df_r, df_c, df_e = n-1, k-1, (n-1)*(k-1)
    ms_r = ss_r / df_r
    ms_e = ss_e / df_e if df_e > 0 else np.nan
    icc_val = float((ms_r - ms_e) / (ms_r + (k-1)*ms_e)) if ms_e else np.nan
    return {"icc_value": icc_val, "n_subjects": n, "n_raters": k}


def bland_altman(m1, m2, ci: float = 0.95) -> dict:
    a, b = _arr(m1), _arr(m2)
    n  = min(len(a), len(b))
    a, b = a[:n], b[:n]
    diff = a - b
    mean_vals = (a + b) / 2
    md   = float(np.mean(diff))
    sd   = float(np.std(diff, ddof=1))
    z    = stats.norm.ppf((1 + ci) / 2)
    loa_u = md + z * sd
    loa_l = md - z * sd
    se_m  = sd / np.sqrt(n)
    tc    = stats.t.ppf((1 + ci) / 2, df=n-1)
    se_l  = sd * np.sqrt(3 / n)
    return {
        "n": n, "mean_diff": md, "std_diff": sd,
        "loa_upper": float(loa_u), "loa_lower": float(loa_l),
        "ci_mean":      (md     - tc*se_m, md     + tc*se_m),
        "ci_loa_upper": (loa_u  - tc*se_l, loa_u  + tc*se_l),
        "ci_loa_lower": (loa_l  - tc*se_l, loa_l  + tc*se_l),
        "mean_vals": mean_vals, "diff": diff,
        "pct_within_loa": float(np.mean((diff >= loa_l) & (diff <= loa_u)) * 100),
        "pearson_r_mean_diff": float(stats.pearsonr(mean_vals, diff)[0]),
    }


def cronbach_alpha(df: pd.DataFrame) -> dict:
    d = df.dropna()
    k = d.shape[1]
    if k < 2:
        return {"error": "Need ≥2 items."}
    item_var = d.var(ddof=1, axis=0).sum()
    total_var = d.sum(axis=1).var(ddof=1)
    alpha = float((k / (k - 1)) * (1 - item_var / total_var)) if total_var > 0 else np.nan
    interp = ("Excellent" if alpha >= 0.9 else
              "Good"      if alpha >= 0.8 else
              "Acceptable" if alpha >= 0.7 else
              "Questionable" if alpha >= 0.6 else
              "Poor"      if alpha >= 0.5 else "Unacceptable")
    return {"cronbach_alpha": alpha, "k_items": k, "n": len(d), "interpretation": interp}


# ═══════════════════════════════════════════════════════════════
# CORRELATION
# ═══════════════════════════════════════════════════════════════

def correlation(x, y, method: str = "pearson") -> dict:
    xv, yv = _arr(x), _arr(y)
    n = min(len(xv), len(yv))
    xv, yv = xv[:n], yv[:n]
    mask = ~(np.isnan(xv) | np.isnan(yv))
    xv, yv = xv[mask], yv[mask]
    n = len(xv)
    if n < 3:
        return {"error": "Need ≥3 paired observations."}
    if method == "spearman":
        r, p = stats.spearmanr(xv, yv)
        name = "Spearman Correlation"
    elif method == "kendall":
        r, p = stats.kendalltau(xv, yv)
        name = "Kendall's Tau"
    else:
        r, p = stats.pearsonr(xv, yv)
        name = "Pearson Correlation"
    ci_l, ci_u = (np.nan, np.nan)
    if method == "pearson" and n > 3:
        z  = np.arctanh(r)
        se = 1 / np.sqrt(n - 3)
        zc = stats.norm.ppf(0.975)
        ci_l, ci_u = float(np.tanh(z - zc*se)), float(np.tanh(z + zc*se))
    return {
        "test": name, "r": float(r), "p_value": float(p), "significant": p < 0.05,
        "n": n, "ci": (ci_l, ci_u), "r_squared": float(r**2),
        "x_vals": xv, "y_vals": yv,
    }


def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> dict:
    num = df.select_dtypes(include=[np.number]).dropna()
    corr = num.corr(method=method)
    n = len(num)
    pmat = pd.DataFrame(np.ones_like(corr.values), index=corr.index, columns=corr.columns)
    for i in range(len(corr.columns)):
        for j in range(len(corr.columns)):
            if i != j:
                xv = num.iloc[:, i].values
                yv = num.iloc[:, j].values
                m2 = ~(np.isnan(xv) | np.isnan(yv))
                if m2.sum() > 2:
                    try:
                        if method == "spearman":
                            _, p = stats.spearmanr(xv[m2], yv[m2])
                        else:
                            _, p = stats.pearsonr(xv[m2], yv[m2])
                        pmat.iloc[i, j] = p
                    except Exception:
                        pass
    return {"corr_matrix": corr, "p_matrix": pmat, "n": n, "method": method}


# ═══════════════════════════════════════════════════════════════
# SURVIVAL ANALYSIS
# ═══════════════════════════════════════════════════════════════

def kaplan_meier(time, event, group=None) -> dict:
    try:
        from lifelines import KaplanMeierFitter
        from lifelines.statistics import logrank_test, multivariate_logrank_test
    except ImportError:
        return {"error": "lifelines not installed. Run: pip install lifelines"}

    t  = np.asarray(time, dtype=float)
    ev = np.asarray(event, dtype=float)
    result: dict = {"groups": {}}

    if group is None:
        mask = ~(np.isnan(t) | np.isnan(ev))
        kmf  = KaplanMeierFitter()
        kmf.fit(t[mask], event_observed=ev[mask])
        result["groups"]["All"] = {"kmf": kmf, "median": float(kmf.median_survival_time_), "n": int(mask.sum())}
        result["logrank"] = None
    else:
        g = np.asarray(group)
        for gv in sorted(set(g[~pd.isna(g)])):
            mask = (g == gv) & ~(np.isnan(t) | np.isnan(ev))
            kmf  = KaplanMeierFitter()
            kmf.fit(t[mask], event_observed=ev[mask], label=str(gv))
            result["groups"][str(gv)] = {"kmf": kmf, "median": float(kmf.median_survival_time_), "n": int(mask.sum())}
        ugroups = sorted(set(g[~pd.isna(g)]))
        if len(ugroups) == 2:
            m1 = (g == ugroups[0]) & ~(np.isnan(t) | np.isnan(ev))
            m2 = (g == ugroups[1]) & ~(np.isnan(t) | np.isnan(ev))
            lr = logrank_test(t[m1], t[m2], event_observed_A=ev[m1], event_observed_B=ev[m2])
            result["logrank"] = {"statistic": float(lr.test_statistic), "p_value": float(lr.p_value), "significant": lr.p_value < 0.05}
        elif len(ugroups) > 2:
            mask = ~(np.isnan(t) | np.isnan(ev) | pd.isna(g))
            mlr  = multivariate_logrank_test(t[mask], g[mask], event_observed=ev[mask])
            result["logrank"] = {"statistic": float(mlr.test_statistic), "p_value": float(mlr.p_value), "significant": mlr.p_value < 0.05}
    return result


def cox_regression(df: pd.DataFrame, time_col: str, event_col: str, covariates: list[str]) -> dict:
    try:
        from lifelines import CoxPHFitter
    except ImportError:
        return {"error": "lifelines not installed. Run: pip install lifelines"}
    cols = [time_col, event_col] + covariates
    df_c = df[cols].dropna()
    cph  = CoxPHFitter()
    try:
        cph.fit(df_c, duration_col=time_col, event_col=event_col, show_progress=False)
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "test": "Cox Proportional Hazards",
        "n": len(df_c), "n_events": int(df_c[event_col].sum()),
        "params_table": cph.summary,
        "concordance_index": float(cph.concordance_index_),
        "aic": float(cph.AIC_partial_),
        "cph": cph,
    }


# ═══════════════════════════════════════════════════════════════
# ADDITIONAL TESTS
# ═══════════════════════════════════════════════════════════════

def odds_ratio_rr(a: int, b: int, c: int, d: int) -> dict:
    """
    2×2 table:  a=exposed cases, b=exposed controls,
                c=unexposed cases, d=unexposed controls
    """
    or_v   = (a * d) / (b * c) if (b * c) > 0 else np.nan
    se_log = np.sqrt(1/a + 1/b + 1/c + 1/d) if all(v > 0 for v in (a,b,c,d)) else np.nan
    or_ci  = (float(np.exp(np.log(or_v) - 1.96*se_log)), float(np.exp(np.log(or_v) + 1.96*se_log))) if not np.isnan(se_log) else (np.nan, np.nan)
    p1     = a / (a + b) if (a + b) > 0 else np.nan
    p2     = c / (c + d) if (c + d) > 0 else np.nan
    rr     = p1 / p2    if p2 > 0 else np.nan
    arr    = (p1 - p2)  if not (np.isnan(p1) or np.isnan(p2)) else np.nan
    nnt    = float(1 / abs(arr)) if arr and arr != 0 else np.nan
    return {
        "odds_ratio": float(or_v), "or_ci": or_ci,
        "relative_risk": float(rr) if not np.isnan(rr) else np.nan,
        "ari": float(arr) if not np.isnan(arr) else np.nan,
        "nnt": nnt, "p_exposed": float(p1), "p_unexposed": float(p2),
    }


def sample_size_means(mean1: float, mean2: float, std: float,
                      alpha: float = 0.05, power: float = 0.80) -> dict:
    from statsmodels.stats.power import TTestIndPower
    es = abs(mean1 - mean2) / std if std > 0 else np.nan
    if np.isnan(es):
        return {"error": "SD must be > 0."}
    n = TTestIndPower().solve_power(effect_size=es, alpha=alpha, power=power)
    return {"n_per_group": int(np.ceil(n)), "total_n": int(np.ceil(n)) * 2,
            "cohens_d": float(es), "power": power, "alpha": alpha}


def sample_size_proportions(p1: float, p2: float,
                             alpha: float = 0.05, power: float = 0.80) -> dict:
    from statsmodels.stats.proportion import proportion_effectsize
    from statsmodels.stats.power import NormalIndPower
    es = proportion_effectsize(p1, p2)
    n  = NormalIndPower().solve_power(effect_size=abs(es), alpha=alpha, power=power)
    return {"n_per_group": int(np.ceil(n)), "total_n": int(np.ceil(n)) * 2,
            "cohens_h": float(es), "power": power, "alpha": alpha}
