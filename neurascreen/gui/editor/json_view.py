"""JSON source view with syntax highlighting and bidirectional sync."""

import json
import logging

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QHBoxLayout

from .syntax_highlighter import JsonHighlighter

logger = logging.getLogger("neurascreen.gui")


class JsonView(QWidget):
    """JSON source editor with syntax highlighting."""

    json_changed = Signal(dict)  # emitted when user edits valid JSON

    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self._updating: bool = False
        self._dark = dark

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Status bar
        status_layout = QHBoxLayout()
        self._status_label = QLabel("JSON Source")
        self._status_label.setProperty("muted", True)
        self._error_label = QLabel("")
        self._error_label.setProperty("error_label", True)
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        status_layout.addWidget(self._error_label)
        layout.addLayout(status_layout)

        # Text editor
        self._editor = QPlainTextEdit()
        self._editor.setProperty("monospace", True)
        font = QFont("JetBrains Mono, Menlo, Consolas, monospace")
        font.setPointSize(11)
        self._editor.setFont(font)
        self._editor.setTabStopDistance(28)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.textChanged.connect(self._on_text_changed)

        self._highlighter = JsonHighlighter(self._editor.document(), dark=dark)

        layout.addWidget(self._editor)

    def set_dark_mode(self, dark: bool) -> None:
        """Update syntax highlighting for dark/light mode."""
        self._dark = dark
        self._highlighter.set_dark_mode(dark)

    def load_scenario(self, data: dict) -> None:
        """Load scenario data into the editor."""
        self._updating = True
        text = json.dumps(data, indent=2, ensure_ascii=False)
        self._editor.setPlainText(text)
        self._error_label.setText("")
        self._updating = False

    def get_scenario(self) -> dict | None:
        """Parse and return the current JSON, or None if invalid."""
        try:
            return json.loads(self._editor.toPlainText())
        except json.JSONDecodeError:
            return None

    def _on_text_changed(self) -> None:
        """Handle text changes: validate JSON and emit signal."""
        if self._updating:
            return

        text = self._editor.toPlainText().strip()
        if not text:
            self._error_label.setText("")
            return

        try:
            data = json.loads(text)
            self._error_label.setText("")
            self.json_changed.emit(data)
        except json.JSONDecodeError as e:
            self._error_label.setText(f"JSON error line {e.lineno}: {e.msg}")

    def set_read_only(self, read_only: bool) -> None:
        """Toggle read-only mode."""
        self._editor.setReadOnly(read_only)

    def is_valid(self) -> bool:
        """Check if current content is valid JSON."""
        try:
            json.loads(self._editor.toPlainText())
            return True
        except (json.JSONDecodeError, ValueError):
            return False
