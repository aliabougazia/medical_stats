"""
app/panel_ai.py – AI Assistant panel (optional LM Studio integration).

Connects to LM Studio's OpenAI-compatible local API (default: localhost:1234).
All statistical work is in Python; the LLM only provides interpretation text.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QLineEdit, QGroupBox, QScrollArea, QFormLayout,
    QComboBox, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from .core import data_store
from .widgets import SectionHeader, Divider, StatusBadge


_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful medical statistics expert assistant. "
    "You help researchers choose appropriate statistical tests and interpret results. "
    "Be concise and clinically relevant. "
    "When you mention statistical tests, briefly explain their assumptions and when to use them. "
    "Always note if results are statistically significant (p < 0.05). "
    "Do NOT perform calculations yourself; the software handles all computations."
)


class _Worker(QObject):
    """Background thread worker for LM Studio API calls."""
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, url: str, messages: list[dict], model: str):
        super().__init__()
        self._url      = url
        self._messages = messages
        self._model    = model

    def run(self):
        try:
            import requests  # noqa: PLC0415
            resp = requests.post(
                f"{self._url}/v1/chat/completions",
                json={
                    "model":       self._model,
                    "messages":    self._messages,
                    "temperature": 0.4,
                    "stream":      False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data    = resp.json()
            content = data["choices"][0]["message"]["content"]
            self.finished.emit(content)
        except Exception as exc:
            self.error.emit(str(exc))


class AIAssistantPanel(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: list[dict[str, str]] = []
        self._worker_thread: threading.Thread | None = None
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)
        root.addWidget(SectionHeader("AI Statistical Assistant"))
        root.addWidget(Divider())

        # Info banner
        info = QLabel(
            "Connect to LM Studio running locally to get AI-assisted test selection "
            "and result interpretation. All statistical computations are performed entirely "
            "by the Python backend – the LLM only provides textual advice."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        root.addWidget(info)

        # ── Connection bar ────────────────────────────────────────────────────
        conn_grp = QGroupBox("LM Studio Connection")
        conn_lay = QHBoxLayout(conn_grp)
        conn_lay.setSpacing(10)

        self._url_edit = QLineEdit("http://localhost:1234")
        self._url_edit.setPlaceholderText("http://localhost:1234")
        conn_lay.addWidget(QLabel("URL:"))
        conn_lay.addWidget(self._url_edit, stretch=1)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.setPlaceholderText("model-name")
        conn_lay.addWidget(QLabel("Model:"))
        conn_lay.addWidget(self._model_combo, stretch=1)

        refresh_btn = QPushButton("🔄  List Models")
        refresh_btn.clicked.connect(self._fetch_models)
        conn_lay.addWidget(refresh_btn)

        connect_btn = QPushButton("⚡  Test Connection")
        connect_btn.setObjectName("primary")
        connect_btn.clicked.connect(self._test_connection)
        conn_lay.addWidget(connect_btn)

        self._conn_badge = StatusBadge()
        self._conn_badge.set_neutral("Disconnected")
        conn_lay.addWidget(self._conn_badge)
        root.addWidget(conn_grp)

        # ── Chat area ─────────────────────────────────────────────────────────
        chat_grp = QGroupBox("Conversation")
        chat_lay = QVBoxLayout(chat_grp)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setMinimumHeight(300)
        self._chat_display.setStyleSheet(
            "background:#0f172a; color:#f1f5f9; "
            "border:1px solid #334155; border-radius:6px; padding:8px;"
        )
        fnt = self._chat_display.font()
        fnt.setPointSize(10); self._chat_display.setFont(fnt)
        chat_lay.addWidget(self._chat_display)

        # Buttons row
        btn_row = QHBoxLayout()
        clear_btn = QPushButton("🗑  Clear Chat")
        clear_btn.clicked.connect(self._clear_chat)
        ctx_btn = QPushButton("📊  Insert Data Context")
        ctx_btn.setToolTip("Appends a summary of the loaded dataset to the next message.")
        ctx_btn.clicked.connect(self._insert_context)
        btn_row.addWidget(clear_btn); btn_row.addWidget(ctx_btn); btn_row.addStretch()
        chat_lay.addLayout(btn_row)
        root.addWidget(chat_grp, stretch=1)

        # ── Input row ─────────────────────────────────────────────────────────
        input_grp = QGroupBox("Your Message")
        input_lay = QVBoxLayout(input_grp)
        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText(
            "Ask about test selection, result interpretation, study design…\n"
            "e.g. 'I have two independent groups with non-normal distributions – which test should I use?'"
        )
        self._input_edit.setMaximumHeight(110)
        self._input_edit.setStyleSheet(
            "background:#1e293b; color:#f1f5f9; "
            "border:1px solid #334155; border-radius:6px; padding:6px;"
        )
        input_lay.addWidget(self._input_edit)

        send_row = QHBoxLayout()
        self._send_btn = QPushButton("▶  Send Message")
        self._send_btn.setObjectName("primary")
        self._send_btn.setMinimumHeight(36)
        self._send_btn.clicked.connect(self._send)
        self._thinking_label = QLabel("")
        self._thinking_label.setObjectName("muted")
        send_row.addStretch(); send_row.addWidget(self._thinking_label)
        send_row.addWidget(self._send_btn)
        input_lay.addLayout(send_row)
        root.addWidget(input_grp)

        # Init system prompt
        self._reset_system()

    # ── Connection ────────────────────────────────────────────────────────────

    def _base_url(self) -> str:
        return self._url_edit.text().rstrip("/")

    def _test_connection(self):
        try:
            import requests
            resp = requests.get(f"{self._base_url()}/v1/models", timeout=5)
            resp.raise_for_status()
            self._conn_badge.set_ok("Connected")
            self.status_message.emit("LM Studio connection OK.")
            self._populate_models(resp.json())
        except Exception as exc:
            self._conn_badge.set_error("Error")
            self.status_message.emit(f"Cannot connect: {exc}")

    def _fetch_models(self):
        try:
            import requests
            resp = requests.get(f"{self._base_url()}/v1/models", timeout=5)
            resp.raise_for_status()
            self._populate_models(resp.json())
        except Exception as exc:
            self.status_message.emit(f"Model list error: {exc}")

    def _populate_models(self, data: dict):
        models = [m.get("id", "") for m in data.get("data", [])]
        self._model_combo.clear()
        self._model_combo.addItems(models)

    # ── Chat ──────────────────────────────────────────────────────────────────

    def _reset_system(self):
        self._messages = [{"role": "system", "content": _DEFAULT_SYSTEM_PROMPT}]

    def _insert_context(self):
        df = data_store.df
        if df is None:
            self._input_edit.insertPlainText("[No data loaded]")
            return
        nrows, ncols = df.shape
        col_info = ", ".join(
            f"{c} ({data_store.column_types.get(c, '?')})"
            for c in df.columns
        )
        ctx = (
            f"\n\n[Dataset context: {nrows} rows × {ncols} columns. "
            f"Columns: {col_info}. "
            f"Missing values: {int(df.isna().sum().sum())}]\n"
        )
        self._input_edit.insertPlainText(ctx)

    def _clear_chat(self):
        self._chat_display.clear()
        self._reset_system()
        self.status_message.emit("Chat cleared.")

    def _send(self):
        user_text = self._input_edit.toPlainText().strip()
        if not user_text:
            return
        url   = self._base_url()
        model = self._model_combo.currentText() or "local-model"

        self._messages.append({"role": "user", "content": user_text})
        self._append_bubble("You", user_text, "#0ea5e9")
        self._input_edit.clear()
        self._send_btn.setEnabled(False)
        self._thinking_label.setText("⏳ Thinking…")

        worker = _Worker(url, list(self._messages), model)
        worker.finished.connect(self._on_response)
        worker.error.connect(self._on_error)

        t = threading.Thread(target=worker.run, daemon=True)
        t.start()
        self._worker_thread = t

    def _on_response(self, text: str):
        self._send_btn.setEnabled(True)
        self._thinking_label.setText("")
        self._messages.append({"role": "assistant", "content": text})
        self._append_bubble("AI Assistant", text, "#8b5cf6")
        self.status_message.emit("AI response received.")

    def _on_error(self, msg: str):
        self._send_btn.setEnabled(True)
        self._thinking_label.setText("")
        self._append_bubble("Error", msg, "#ef4444")
        self.status_message.emit(f"AI error: {msg}")

    def _append_bubble(self, sender: str, text: str, color: str):
        cursor = self._chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._chat_display.setTextCursor(cursor)

        self._chat_display.append(
            f'<p style="margin:0 0 2px 0;">'
            f'<span style="color:{color}; font-weight:700;">{sender}</span>'
            f'</p>'
            f'<p style="margin:0 0 12px 0; color:#e2e8f0; white-space:pre-wrap;">'
            f'{text.replace(chr(10), "<br>")}'
            f'</p>'
        )
        self._chat_display.verticalScrollBar().setValue(
            self._chat_display.verticalScrollBar().maximum()
        )
