# MedStat Pro

**Advanced Medical Research Statistical Analysis**

> **Disclaimer:** This application was built by the author for personal research use. Others are welcome to use it freely. However, the author provides this software *as-is*, without warranty of any kind, and **cannot accept any liability** for decisions made, clinical or otherwise, based on results produced by this application. All statistical outputs should be interpreted by a qualified professional. This tool is not a substitute for expert statistical or medical advice.

---

MedStat Pro is a desktop application for medical researchers, clinicians, and epidemiologists. It provides a full suite of descriptive, inferential, diagnostic, regression, reliability, and survival statistics — all computed locally with Python scientific libraries. An optional LM Studio integration lets you chat with a local LLM for guidance on test selection and result interpretation, while every statistical calculation remains fully independent of AI.

---

## Table of Contents

- [Screenshots / UI Overview](#ui-overview)
- [Features](#features)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Module Architecture](#module-architecture)
- [Panels & Functionality](#panels--functionality)
  - [Data Manager](#1-data-manager)
  - [Descriptive Statistics](#2-descriptive-statistics)
  - [Diagnostic Tests](#3-diagnostic-tests)
  - [Statistical Tests](#4-statistical-tests)
  - [Regression](#5-regression)
  - [Reliability](#6-reliability)
  - [Correlation](#7-correlation)
  - [Survival Analysis](#8-survival-analysis)
  - [AI Assistant](#9-ai-assistant)
- [Statistical Engine](#statistical-engine)
- [Data Input Formats](#data-input-formats)
- [Saving & Exporting Results](#saving--exporting-results)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)

---

## UI Overview

MedStat Pro uses a **dark slate / cyan theme** built entirely in PyQt6 QSS:

| Element | Description |
|---|---|
| **Sidebar** | Fixed-width collapsible navigation with icon + label buttons |
| **Content area** | Stacked panels, each with tabbed sub-views |
| **Status bar** | Live data badge (rows × columns) + contextual messages |
| **Splash screen** | Gradient splash on launch |
| **Embedded plots** | Matplotlib figures inside the UI with navigation toolbar, zoom, pan, save, and copy-to-clipboard |
| **Results tables** | Colour-coded p-values (green = significant, red = not significant), copy to clipboard, export to CSV |

Colour palette: `#0f172a` dark background · `#0ea5e9` cyan accent · `#8b5cf6` purple accent · `#22c55e` success.

---

## Features

### Data Input
- **Paste text** — CSV, TSV, semicolon-separated, or space-separated with auto-detection
- **Import Excel** (`.xlsx`, `.xls`) or flat files (`.csv`, `.tsv`, `.txt`)
- **Auto column-type detection** — quantitative, categorical, binary, time (survival), event (survival)
- **Manual type override** per column with a combo-box editor

### Descriptive Statistics
- Mean ± SD, median, IQR, min, max
- 95% confidence interval for the mean
- Skewness, n, missing count
- Frequency tables with n and % for categorical columns
- Normality tests: Shapiro-Wilk, D'Agostino-Pearson, Kolmogorov-Smirnov
- Plots: histogram (with mean / median lines), violin plot, bar chart with percentages, Q-Q plot

### Diagnostic Tests
**Manual 2×2 table entry:**
- Sensitivity · Specificity · PPV · NPV · Diagnostic Accuracy (all with 95% Wilson CI)
- F1 Score · LR+ · LR− · Diagnostic Odds Ratio · Prevalence
- Horizontal bar visual of all diagnostic metrics

**ROC Curve (from data columns):**
- AUC with bootstrapped 95% CI
- Youden's J index
- Optimal threshold · Sensitivity and Specificity at every curve point
- PPV, NPV, and Accuracy at the optimal threshold
- Full curve data table (FPR, TPR, threshold for all points)
- ROC plot with AUC fill, optimal point annotation

### Statistical Tests
**Parametric:**
- One-Sample T-Test (with effect size d, 95% CI of mean)
- Independent (Welch) T-Test (effect size d, CI of difference)
- Paired T-Test (effect size d, CI of difference)
- One-Way ANOVA (with Tukey HSD post-hoc)
- Two-Way ANOVA (main effects + interaction)
- MANOVA (Wilks' Lambda)

**Non-Parametric:**
- Mann-Whitney U Test (with rank-biserial r)
- Wilcoxon Signed-Rank Test
- Kruskal-Wallis Test (with Dunn post-hoc)
- Friedman Test

**Categorical:**
- Chi-Square test / Fisher's Exact test (auto-switched on cell size)
- McNemar's Test (paired proportions)
- Odds Ratio & Relative Risk (with 95% CI, NNT/NNH)

**Sample Size Calculator:**
- Two independent means (power, alpha, common SD)
- Two independent proportions (power, alpha)

All tests display: statistic, p-value (colour-coded), effect size, 95% CI, interpretation, and an associated plot.

### Regression
- **Simple Linear Regression** — β, SE, t, p, 95% CI, R², adjusted R², RMSE, F-stat, scatter with regression line and 95% CI band
- **Multiple Linear Regression** — coefficient table, model fit summary (R², adj. R², AIC, BIC), VIF / collinearity check, diagnostic plots (residuals vs fitted, Q-Q residuals, scale-location, leverage)
- **Logistic Regression** — coefficients, odds ratios with 95% CI, Wald p-values, model fit (log-likelihood, AIC, BIC, McFadden's R²), ROC plot, confusion matrix
- **Poisson Regression** — IRR (Incident Rate Ratios), 95% CI, model fit

### Reliability
- **Cohen's Kappa** — weighted/unweighted kappa, SE, 95% CI, interpretation band
- **Intraclass Correlation Coefficient (ICC)** — ICC(1), ICC(2,1), ICC(3,1); all with 95% CI and reliability interpretation
- **Bland-Altman Analysis** — bias, 95% limits of agreement, proportional bias test, Bland-Altman plot with CI bands and all annotated limits
- **Cronbach's Alpha** — overall α, per-item "alpha if deleted" table, inter-item correlation matrix, split-half reliability

### Correlation
- **Bivariate Correlation** — Pearson r, Spearman ρ, Kendall τ; with p-value, 95% CI (Fisher Z), and scatter plot with regression line
- **Correlation Matrix** — full pairwise matrix; separate heatmaps for r-values and p-values; pair plot of selected variables

### Survival Analysis
- **Kaplan-Meier Estimator** — with optional grouping; log-rank test p-value; KM curves with 95% CI bands, median survival, event/censored counts, risk table
- **Cox Proportional Hazards Regression** — hazard ratios (HR) with 95% CI, Wald p-values, concordance index (C-statistic), log-likelihood, AIC; baseline hazard plot

### AI Assistant (Optional)
- Connects to **LM Studio** at `http://localhost:1234` (configurable URL)
- Auto-fetches available models from the running LM Studio server
- System prompt pre-loaded with medical statistics expertise context
- Streaming-style chat interface with message history
- Quick-action prompts: "Help me choose a test", "Interpret my results", "Explain normality", "When to use non-parametric tests"
- All statistical calculations remain Python-only; the LLM is advisory only

---

## Installation

### Requirements
- Python 3.11
- Conda (recommended) or virtualenv

### 1. Create and activate the environment

```bash
conda create -n medical_stats python=3.11
conda activate medical_stats
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**

| Package | Purpose |
|---|---|
| `PyQt6 >=6.4` | GUI framework |
| `pandas >=2.0` | Data handling |
| `numpy >=1.24` | Numerical computation |
| `scipy >=1.11` | Statistical tests |
| `statsmodels >=0.14` | Regression, ANOVA, MANOVA |
| `scikit-learn >=1.3` | Logistic regression, ROC |
| `matplotlib >=3.7` | Embedded plots |
| `seaborn >=0.13` | Statistical plots |
| `openpyxl >=3.1` | Excel file reading |
| `pingouin >=0.5` | ICC, Cohen's kappa, effect sizes |
| `lifelines >=0.27` | Kaplan-Meier, Cox regression |
| `requests >=2.31` | LM Studio API communication |

---

## Running the App

```bash
conda activate medical_stats
python main.py
```

---

## Module Architecture

```
medical_stats/
├── main.py               # Entry point; splash screen; QApplication setup
├── requirements.txt
└── app/
    ├── __init__.py
    ├── core.py           # DataStore singleton; parsing helpers; p-value formatters
    ├── styles.py         # Global QSS dark theme (Slate/Cyan palette)
    ├── widgets.py        # Reusable: PlotWidget, ResultsTable, SectionHeader, StatusBadge
    ├── main_window.py    # MainWindow; sidebar navigation; panel stacking
    ├── statistics.py     # All statistical computation (pure Python/SciPy/statsmodels)
    ├── panel_data.py     # Data Manager panel
    ├── panel_descriptive.py
    ├── panel_diagnostic.py
    ├── panel_tests.py
    ├── panel_regression.py
    ├── panel_reliability.py
    ├── panel_correlation.py
    ├── panel_survival.py
    └── panel_ai.py
```

### Key design decisions

- **`DataStore` singleton** (`app/core.py`) — all panels share a single in-memory DataFrame; panels register callbacks via `add_listener()` and auto-refresh when data changes.
- **`statistics.py` is UI-free** — every statistical function returns a plain `dict` or `pd.DataFrame`; panels are responsible only for display.
- **`PlotWidget`** embeds a Matplotlib `FigureCanvas` with the Qt navigation toolbar; every plot has Save (PNG/PDF/SVG/TIFF at 300 dpi) and Copy to Clipboard buttons.
- **`ResultsTable`** wraps `QTableWidget` with automatic p-value colour coding, Copy as TSV, and Export as CSV.
- **Lazy panel imports** — panels are imported after the splash screen closes, keeping startup time fast.

---

## Panels & Functionality

### 1. Data Manager

- Paste area for raw text data (CSV / TSV / space-separated)
- File browser for Excel (`.xlsx`/`.xls`) and flat files
- Live preview table (first 100 rows)
- Per-column type editor — override auto-detection to `quantitative`, `categorical`, `binary`, `time (survival)`, `event (survival)`
- Data summary: rows, columns, total missing values
- Status badge updates across all panels on data load

### 2. Descriptive Statistics

- Multi-column selector (Ctrl+click)
- Options: histogram, box/violin, bar chart, normality tests
- **Summary table**: n, missing, mean ± SD, median (IQR), min, max, 95% CI, skewness
- **Frequencies table**: value, count n, percentage %
- **Normality table**: Shapiro-Wilk / D'Agostino / KS statistic, p, normal? (Yes/No)
- **Plots**: histogram with mean+median lines · violin plot · bar chart with % labels · Q-Q plot with R²

### 3. Diagnostic Tests

**Tab 1 – 2×2 Table Entry**
- Visual 2×2 grid: TP, FP, FN, TN (spin boxes)
- Computes: Sensitivity, Specificity, PPV, NPV, Accuracy (all with 95% CI), F1, LR+, LR−, DOR, Prevalence
- Horizontal bar chart of all metrics

**Tab 2 – ROC Curve**
- Select score column and binary label column from loaded data
- Computes full ROC curve, AUC (with bootstrap 95% CI), Youden's J, optimal threshold
- Curve data table (FPR, TPR, threshold for every operating point)
- ROC plot with AUC fill and optimal point annotated with sensitivity/specificity

### 4. Statistical Tests

Context-sensitive config panel changes based on selected test.

| Test | Config inputs |
|---|---|
| One-Sample T-Test | Variable column, hypothesised mean μ₀ |
| Independent T-Test | Outcome column, group column (2 groups) |
| Paired T-Test | Variable 1 (before), Variable 2 (after) |
| One-Way ANOVA | Outcome column, group column; Tukey HSD post-hoc |
| Two-Way ANOVA | Outcome, Factor 1, Factor 2 |
| MANOVA | Multiple outcome columns, Factor column |
| Mann-Whitney U | Outcome column, group column (2 groups) |
| Wilcoxon Signed-Rank | Two paired columns |
| Kruskal-Wallis | Outcome, group column; Dunn post-hoc |
| Friedman Test | Multiple repeated-measure columns |
| Chi-Square / Fisher | Two categorical columns; auto-switches to Fisher on sparse cells |
| McNemar's Test | Two paired binary columns |
| Odds Ratio & RR | Manual a/b/c/d entry; OR, RR, 95% CI, NNT |
| Sample Size (means) | Mean 1, Mean 2, SD, power, alpha |
| Sample Size (props) | Proportion 1, Proportion 2, power, alpha |

All tests output: test statistic, degrees of freedom, p-value (colour-coded, starred), effect size, 95% CI where applicable, and an interpretation sentence.

### 5. Regression

- **Model selector**: Simple Linear · Multiple Linear · Logistic · Poisson
- Outcome and predictor column selectors
- **Output tabs**:
  - Coefficients table (β or log-OR, SE, t/z/Wald, p, 95% CI)
  - Model fit (R², AIC, BIC, log-likelihood, F-stat, RMSE, McFadden R²)
  - VIF / Collinearity check
  - Diagnostic plots (residuals vs fitted, Q-Q, scale-location, leverage / Cook's D)
  - Scatter + regression line (simple) or ROC plot (logistic)

### 6. Reliability

- **Cohen's Kappa**: two rater columns → κ, SE, 95% CI, weighted/unweighted, interpretation
- **ICC**: wide-format rater columns → ICC(1), ICC(2,1), ICC(3,1) with 95% CI and reliability label
- **Bland-Altman**: two measurement columns → bias, SD of differences, 95% LoA, proportional bias test, annotated Bland-Altman plot
- **Cronbach's α**: item columns → overall α, item-total correlations, α-if-item-deleted, split-half reliability

### 7. Correlation

- **Bivariate**: X and Y columns, method (Pearson / Spearman / Kendall) → r, p, 95% CI, scatter plot with regression line
- **Correlation Matrix**: multi-column selector → full r-matrix table, p-value matrix, heatmap (colour-coded), pair plot grid

### 8. Survival Analysis

- **Kaplan-Meier**: time column, event column, optional group column → log-rank p-value, median survival, KM curve with 95% CI bands, risk table
- **Cox Regression**: time, event, and covariate columns → HR table (with 95% CI, Wald p), concordance index, AIC, baseline hazard plot

### 9. AI Assistant

- Configurable LM Studio server URL (default: `http://localhost:1234`)
- Fetches model list from running server; dropdown for model selection
- Connection test button with status badge
- Chat interface with scrollable history
- Context-aware: the system prompt instructs the LLM to act as a medical statistician
- Quick prompts for common queries
- Clear chat button
- All statistical computations are performed independently by the Python backend

---

## Statistical Engine

`app/statistics.py` contains every statistical function as a standalone, testable unit:

| Function | Library used |
|---|---|
| `quantitative_stats` | numpy, scipy.stats |
| `categorical_stats` | pandas |
| `normality_tests` | scipy.stats (Shapiro-Wilk, D'Agostino, KS) |
| `diagnostic_metrics` | pure arithmetic + Wilson CI |
| `roc_analysis` | sklearn.metrics + bootstrap |
| `t_test_one_sample / independent / paired` | scipy.stats |
| `mann_whitney`, `wilcoxon_signed_rank` | scipy.stats |
| `chi_square`, `mcnemar` | scipy.stats |
| `one_way_anova` | scipy.stats + pingouin (Tukey HSD) |
| `kruskal_wallis` | scipy.stats + scikit_posthocs |
| `friedman_test` | scipy.stats |
| `two_way_anova` | statsmodels OLS |
| `manova_test` | statsmodels MANOVA |
| `simple_linear_regression` | statsmodels OLS |
| `multiple_linear_regression` | statsmodels OLS + VIF |
| `logistic_regression` | statsmodels Logit |
| `poisson_regression` | statsmodels GLM Poisson |
| `cohens_kappa` | sklearn.metrics |
| `icc_analysis` | pingouin |
| `bland_altman` | pure arithmetic |
| `cronbach_alpha` | pure arithmetic + pandas |
| `correlation` | scipy.stats (Pearson / Spearman / Kendall) |
| `correlation_matrix` | pandas + scipy.stats |
| `kaplan_meier` | lifelines |
| `cox_regression` | lifelines CoxPHFitter |
| `odds_ratio_rr` | pure arithmetic + Wilson CI |
| `sample_size_means / proportions` | statsmodels proportion_effectsize / TTestIndPower |

---

## Data Input Formats

| Format | Method |
|---|---|
| Pasted CSV | First row = headers; comma-separated |
| Pasted TSV | First row = headers; tab-separated |
| Pasted space/semicolon separated | Auto-detected from first line |
| `.xlsx` / `.xls` | File browser → openpyxl |
| `.csv` / `.tsv` / `.txt` | File browser → auto-delimiter detection |

**Notes:**
- The first row must contain column names.
- Numeric columns are automatically coerced; non-numeric remain as strings (categorical).
- Missing values (`NaN`, empty cells) are handled gracefully in all analyses.

---

## Saving & Exporting Results

| Output | How |
|---|---|
| Plot as PNG (300 dpi) | "💾 Save Plot" button in every plot tab |
| Plot as PDF / SVG / TIFF | Same dialog, choose format |
| Plot to clipboard | "📋 Copy" button copies as PNG |
| Table as CSV | "💾 Export CSV" button in every results table |
| Table to clipboard (TSV) | "📋 Copy Table" button |
| Matplotlib toolbar | Zoom, pan, navigate, save via standard toolbar |

---

## Tech Stack

| Layer | Technology |
|---|---|
| GUI | PyQt6 6.4+ |
| Plotting | Matplotlib 3.7+ (embedded QtAgg backend) + Seaborn 0.13+ |
| Data | Pandas 2.0+ / NumPy 1.24+ |
| Statistics | SciPy 1.11+ / Statsmodels 0.14+ / Scikit-learn 1.3+ |
| Advanced stats | Pingouin 0.5+ (ICC, kappa) / Lifelines 0.27+ (KM, Cox) |
| File I/O | OpenPyXL 3.1+ |
| AI integration | Requests 2.31+ (LM Studio OpenAI-compatible API) |
| Language | Python 3.11 |

---

## Project Structure

```
medical_stats/
├── main.py
├── requirements.txt
├── .gitignore
└── app/
    ├── __init__.py
    ├── core.py
    ├── styles.py
    ├── widgets.py
    ├── main_window.py
    ├── statistics.py
    ├── panel_data.py
    ├── panel_descriptive.py
    ├── panel_diagnostic.py
    ├── panel_tests.py
    ├── panel_regression.py
    ├── panel_reliability.py
    ├── panel_correlation.py
    ├── panel_survival.py
    └── panel_ai.py
```

---

## License

MIT
