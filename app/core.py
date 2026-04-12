"""
app/core.py – Shared DataStore singleton and utility helpers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Callable, Optional


class DataStore:
    """Application-wide singleton holding the active DataFrame."""

    _instance: Optional["DataStore"] = None

    def __new__(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._df: Optional[pd.DataFrame] = None
            cls._instance._filename: str = ""
            cls._instance._col_types: dict[str, str] = {}
            cls._instance._listeners: list[Callable] = []
        return cls._instance

    # ── Properties ───────────────────────────────────────────────

    @property
    def df(self) -> Optional[pd.DataFrame]:
        return self._df

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def column_types(self) -> dict[str, str]:
        return self._col_types

    @property
    def has_data(self) -> bool:
        return self._df is not None and len(self._df) > 0

    # ── Mutators ─────────────────────────────────────────────────

    def set_data(self, df: pd.DataFrame, filename: str = "") -> None:
        self._df = df.copy()
        self._filename = filename
        self._auto_detect_types()
        self._notify()

    def set_column_type(self, col: str, typ: str) -> None:
        """typ: 'quantitative' | 'categorical' | 'binary' | 'time' | 'event'"""
        self._col_types[col] = typ
        self._notify()

    def clear(self) -> None:
        self._df = None
        self._filename = ""
        self._col_types = {}
        self._notify()

    # ── Column helpers ────────────────────────────────────────────

    def cols_of_type(self, *types: str) -> list[str]:
        return [c for c, t in self._col_types.items() if t in types]

    def numeric_cols(self) -> list[str]:
        if self._df is None:
            return []
        return list(self._df.select_dtypes(include=[np.number]).columns)

    def all_cols(self) -> list[str]:
        return list(self._df.columns) if self._df is not None else []

    # ── Listeners ─────────────────────────────────────────────────

    def add_listener(self, cb: Callable) -> None:
        if cb not in self._listeners:
            self._listeners.append(cb)

    def remove_listener(self, cb: Callable) -> None:
        self._listeners = [x for x in self._listeners if x is not cb]

    def _notify(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass

    # ── Auto-detection ────────────────────────────────────────────

    def _auto_detect_types(self) -> None:
        if self._df is None:
            return
        self._col_types = {}
        for col in self._df.columns:
            s = self._df[col].dropna()
            if len(s) == 0:
                self._col_types[col] = "categorical"
                continue
            n_unique = s.nunique()
            if pd.api.types.is_numeric_dtype(self._df[col]):
                if n_unique == 2:
                    self._col_types[col] = "binary"
                elif n_unique <= 8:
                    self._col_types[col] = "categorical"
                else:
                    self._col_types[col] = "quantitative"
            else:
                self._col_types[col] = "categorical"


# Module-level singleton
data_store = DataStore()


# ── Parsing helpers ────────────────────────────────────────────────────────────

def parse_pasted_text(text: str) -> tuple[pd.DataFrame, str]:
    """
    Parse pasted text (CSV / TSV / space-separated) into a DataFrame.
    Returns (df, error_message).
    """
    import io
    text = text.strip()
    if not text:
        return pd.DataFrame(), "No text provided."

    # Detect delimiter
    first_line = text.splitlines()[0]
    if "\t" in first_line:
        sep = "\t"
    elif "," in first_line:
        sep = ","
    elif ";" in first_line:
        sep = ";"
    else:
        sep = r"\s+"

    try:
        df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
        # Try to coerce numeric columns
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
        return df, ""
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def format_pvalue(p: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "N/A"
    if p < 0.001:
        return "<0.001"
    if p < 0.05:
        return f"{p:.4f} *"
    return f"{p:.4f}"


def format_ci(lo: float, hi: float, pct: bool = True, decimals: int = 2) -> str:
    if any(isinstance(v, float) and np.isnan(v) for v in (lo, hi)):
        return "N/A"
    if pct:
        return f"({lo*100:.{decimals}f}% – {hi*100:.{decimals}f}%)"
    return f"({lo:.{decimals}f} – {hi:.{decimals}f})"


def sig_stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"
