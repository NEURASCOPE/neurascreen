"""JSON syntax highlighter for QPlainTextEdit."""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class JsonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON content."""

    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._setup_formats(dark)

    def _setup_formats(self, dark: bool) -> None:
        self._rules.clear()

        # String keys (before colon)
        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor("#14B8A6") if dark else QColor("#0F766E"))
        key_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'"([^"\\]|\\.)*"\s*(?=:)'), key_fmt))

        # String values
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#F59E0B") if dark else QColor("#B45309"))
        self._rules.append((re.compile(r':\s*"([^"\\]|\\.)*"'), str_fmt))

        # Standalone strings (in arrays)
        str2_fmt = QTextCharFormat()
        str2_fmt.setForeground(QColor("#F59E0B") if dark else QColor("#B45309"))
        self._rules.append((re.compile(r'(?<=[\[,])\s*"([^"\\]|\\.)*"'), str2_fmt))

        # Numbers
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#3B82F6") if dark else QColor("#2563EB"))
        self._rules.append((re.compile(r'\b-?\d+\.?\d*([eE][+-]?\d+)?\b'), num_fmt))

        # Booleans and null
        bool_fmt = QTextCharFormat()
        bool_fmt.setForeground(QColor("#EF4444") if dark else QColor("#DC2626"))
        bool_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'\b(true|false|null)\b'), bool_fmt))

        # Braces and brackets
        brace_fmt = QTextCharFormat()
        brace_fmt.setForeground(QColor("#94A3B8") if dark else QColor("#475569"))
        self._rules.append((re.compile(r'[{}\[\]]'), brace_fmt))

        # Colon and comma
        punct_fmt = QTextCharFormat()
        punct_fmt.setForeground(QColor("#64748B") if dark else QColor("#94A3B8"))
        self._rules.append((re.compile(r'[,:]'), punct_fmt))

    def set_dark_mode(self, dark: bool) -> None:
        """Reconfigure colors for dark or light mode."""
        self._setup_formats(dark)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
