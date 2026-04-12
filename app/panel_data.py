"""
app/panel_data.py – Data Manager panel: paste text or load Excel.
"""
from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QComboBox, QGroupBox, QScrollArea, QSplitter,
    QSizePolicy, QAbstractItemView, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from .core import data_store, parse_pasted_text
from .widgets import SectionHeader, Divider, StatusBadge


_TYPE_OPTIONS = ["auto", "quantitative", "categorical", "binary", "time (survival)", "event (survival)"]
_TYPE_MAP = {
    "auto":             "auto",
    "quantitative":     "quantitative",
    "categorical":      "categorical",
    "binary":           "binary",
    "time (survival)":  "time",
    "event (survival)": "event",
}


class DataPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        root.addWidget(SectionHeader("Data Manager"))
        root.addWidget(Divider())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: input ───────────────────────────────────────────────────────
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 8, 0)
        llay.setSpacing(8)

        grp_paste = QGroupBox("Paste Data (CSV / TSV / Space-separated)")
        gp_lay    = QVBoxLayout(grp_paste)
        self._paste_edit = QPlainTextEdit()
        self._paste_edit.setPlaceholderText(
            "Paste your data here.\n"
            "First row should be column headers.\n\n"
            "Example (tab-separated):\n"
            "Age\tBMI\tGroup\n"
            "34\t22.5\tA\n"
            "45\t28.1\tB"
        )
        self._paste_edit.setMinimumHeight(200)
        gp_lay.addWidget(self._paste_edit)

        load_paste_btn = QPushButton("⬆  Load Pasted Data")
        load_paste_btn.setObjectName("primary")
        load_paste_btn.clicked.connect(self._load_pasted)
        gp_lay.addWidget(load_paste_btn)
        llay.addWidget(grp_paste)

        grp_file = QGroupBox("Import from File")
        gf_lay   = QHBoxLayout(grp_file)
        self._file_label = QLabel("No file selected")
        self._file_label.setObjectName("muted")
        self._file_label.setWordWrap(True)
        load_file_btn = QPushButton("📂  Browse…")
        load_file_btn.clicked.connect(self._load_file)
        gf_lay.addWidget(self._file_label, stretch=1)
        gf_lay.addWidget(load_file_btn)
        llay.addWidget(grp_file)

        clear_btn = QPushButton("🗑  Clear Data")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear)
        llay.addWidget(clear_btn)
        llay.addStretch()
        left.setMaximumWidth(400)

        # ── Right: preview + column types ─────────────────────────────────────
        right     = QWidget()
        rlay      = QVBoxLayout(right)
        rlay.setContentsMargins(8, 0, 0, 0)
        rlay.setSpacing(8)

        info_row  = QHBoxLayout()
        self._info_label = QLabel("No data loaded.")
        self._info_label.setObjectName("muted")
        self._status_badge = StatusBadge("No data")
        self._status_badge.set_neutral("No data")
        info_row.addWidget(self._info_label)
        info_row.addStretch()
        info_row.addWidget(self._status_badge)
        rlay.addLayout(info_row)

        # Preview table
        grp_prev = QGroupBox("Data Preview  (first 100 rows)")
        gv_lay   = QVBoxLayout(grp_prev)
        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.verticalHeader().setVisible(True)
        self._preview_table.setMinimumHeight(220)
        gv_lay.addWidget(self._preview_table)
        rlay.addWidget(grp_prev, stretch=2)

        # Column type editor
        grp_types = QGroupBox("Column Types  (override auto-detection)")
        gt_lay    = QVBoxLayout(grp_types)
        self._types_table = QTableWidget()
        self._types_table.setColumnCount(3)
        self._types_table.setHorizontalHeaderLabels(["Column", "Detected Type", "Set Type"])
        self._types_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._types_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._types_table.setMinimumHeight(160)
        gt_lay.addWidget(self._types_table)

        apply_types_btn = QPushButton("✔  Apply Column Types")
        apply_types_btn.setObjectName("primary")
        apply_types_btn.clicked.connect(self._apply_types)
        gt_lay.addWidget(apply_types_btn)
        rlay.addWidget(grp_types, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_pasted(self):
        text = self._paste_edit.toPlainText()
        df, err = parse_pasted_text(text)
        if err:
            self.status_message.emit(f"Parse error: {err}")
            return
        data_store.set_data(df, filename="<pasted>")
        self._refresh_ui()
        self.status_message.emit(f"Loaded {len(df)} rows × {len(df.columns)} columns from clipboard.")

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Data File", "",
            "Excel / CSV (*.xlsx *.xls *.csv *.tsv *.txt)",
        )
        if not path:
            return
        try:
            if path.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(path)
            else:
                # try CSV / TSV
                for sep in (",", "\t", ";"):
                    try:
                        df = pd.read_csv(path, sep=sep)
                        if df.shape[1] > 1:
                            break
                    except Exception:
                        continue
        except Exception as exc:
            self.status_message.emit(f"File error: {exc}")
            return
        # Coerce numerics
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
        data_store.set_data(df, filename=path.split("/")[-1])
        self._file_label.setText(path.split("/")[-1])
        self._refresh_ui()
        self.status_message.emit(f"Loaded '{path.split('/')[-1]}': {len(df)} rows × {len(df.columns)} columns.")

    def _clear(self):
        data_store.clear()
        self._paste_edit.clear()
        self._file_label.setText("No file selected")
        self._preview_table.clear()
        self._preview_table.setRowCount(0)
        self._preview_table.setColumnCount(0)
        self._types_table.clear()
        self._types_table.setRowCount(0)
        self._info_label.setText("No data loaded.")
        self._status_badge.set_neutral("No data")
        self.status_message.emit("Data cleared.")

    # ── UI refresh ────────────────────────────────────────────────────────────

    def _refresh_ui(self):
        df = data_store.df
        if df is None:
            return
        nrows, ncols = df.shape
        self._info_label.setText(
            f"<b>{nrows}</b> rows  ×  <b>{ncols}</b> columns  "
            f"| Missing values: <b>{int(df.isna().sum().sum())}</b>"
        )
        self._status_badge.set_ok(f"{nrows}×{ncols}")

        # Preview
        preview = df.head(100)
        self._preview_table.clear()
        self._preview_table.setRowCount(len(preview))
        self._preview_table.setColumnCount(len(preview.columns))
        self._preview_table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        for r in range(len(preview)):
            for c in range(len(preview.columns)):
                val = preview.iat[r, c]
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._preview_table.setItem(r, c, item)

        # Types table with combo boxes
        self._type_combos: dict[str, QComboBox] = {}
        self._types_table.setRowCount(ncols)
        for i, col in enumerate(df.columns):
            detected = data_store.column_types.get(col, "?")
            self._types_table.setItem(i, 0, QTableWidgetItem(str(col)))
            self._types_table.setItem(i, 1, QTableWidgetItem(detected))
            combo = QComboBox()
            combo.addItems(_TYPE_OPTIONS)
            combo.setCurrentText("auto")
            self._types_table.setCellWidget(i, 2, combo)
            self._type_combos[col] = combo

    def _apply_types(self):
        df = data_store.df
        if df is None:
            return
        for col, combo in self._type_combos.items():
            choice = combo.currentText()
            if choice != "auto":
                data_store.set_column_type(col, _TYPE_MAP[choice])
        self.status_message.emit("Column types applied.")
