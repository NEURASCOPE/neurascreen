"""Console widget: read-only log viewer with colored output."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QApplication,
)

logger = logging.getLogger("neurascreen.gui")


class ConsoleWidget(QWidget):
    """Read-only console with colored log output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Text area
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setProperty("monospace", True)
        font = QFont("JetBrains Mono, Menlo, Consolas, monospace")
        font.setPointSize(11)
        self._text.setFont(font)
        self._text.setMaximumBlockCount(5000)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 4, 4, 4)
        btn_layout.setSpacing(4)

        btn_clear = QPushButton("Clear")
        btn_clear.setToolTip("Clear console output")
        btn_clear.clicked.connect(self.clear)

        btn_copy = QPushButton("Copy All")
        btn_copy.setToolTip("Copy all output to clipboard")
        btn_copy.clicked.connect(self._on_copy)

        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_copy)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Formats — info uses no forced foreground (inherits from QSS theme)
        self._fmt_info = QTextCharFormat()

        self._fmt_warning = QTextCharFormat()
        self._fmt_warning.setForeground(QColor("#F59E0B"))

        self._fmt_error = QTextCharFormat()
        self._fmt_error.setForeground(QColor("#EF4444"))

        self._fmt_debug = QTextCharFormat()
        self._fmt_debug.setForeground(QColor("#64748B"))

        self._fmt_success = QTextCharFormat()
        self._fmt_success.setForeground(QColor("#22C55E"))

    def append_line(self, text: str) -> None:
        """Append a line with automatic color based on content."""
        text_lower = text.lower()

        if "error" in text_lower or "fail" in text_lower or "traceback" in text_lower:
            fmt = self._fmt_error
        elif "warning" in text_lower or "warn" in text_lower:
            fmt = self._fmt_warning
        elif "debug" in text_lower:
            fmt = self._fmt_debug
        elif "done" in text_lower or "success" in text_lower or "passed" in text_lower:
            fmt = self._fmt_success
        else:
            fmt = self._fmt_info

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def append_info(self, text: str) -> None:
        """Append an info-level line."""
        self._append_with_format(text, self._fmt_info)

    def append_error(self, text: str) -> None:
        """Append an error-level line."""
        self._append_with_format(text, self._fmt_error)

    def append_success(self, text: str) -> None:
        """Append a success line."""
        self._append_with_format(text, self._fmt_success)

    def _append_with_format(self, text: str, fmt: QTextCharFormat) -> None:
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self) -> None:
        """Clear all console output."""
        self._text.clear()

    def _on_copy(self) -> None:
        """Copy all text to clipboard."""
        QApplication.clipboard().setText(self._text.toPlainText())

    def text(self) -> str:
        """Return all console text."""
        return self._text.toPlainText()
