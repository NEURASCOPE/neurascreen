"""Live event feed: displays captured browser events in real time."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
)

logger = logging.getLogger("neurascreen.gui")

# Colors per event type
EVENT_COLORS = {
    "click": QColor("#22D3EE"),     # cyan
    "navigate": QColor("#A78BFA"),  # purple
    "scroll": QColor("#FBBF24"),    # amber
    "key": QColor("#34D399"),       # emerald
}
DEFAULT_COLOR = QColor("#94A3B8")   # slate


class EventFeed(QWidget):
    """Scrolling list of captured browser events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._event_count = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 0)
        self._label = QLabel("Events: 0")
        self._label.setProperty("muted", True)
        header.addWidget(self._label)
        header.addStretch()

        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setToolTip("Clear event list")
        self._btn_clear.clicked.connect(self.clear)
        header.addWidget(self._btn_clear)
        layout.addLayout(header)

        # List
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self._list)

    def add_event(self, event: dict) -> None:
        """Add a captured event to the feed."""
        self._event_count += 1
        self._label.setText(f"Events: {self._event_count}")

        event_type = event.get("type", "unknown")
        text = format_event(event)

        item = QListWidgetItem(text)
        color = EVENT_COLORS.get(event_type, DEFAULT_COLOR)
        item.setForeground(color)
        self._list.addItem(item)
        self._list.scrollToBottom()

    def clear(self) -> None:
        """Clear all events."""
        self._list.clear()
        self._event_count = 0
        self._label.setText("Events: 0")

    @property
    def event_count(self) -> int:
        return self._event_count


def format_event(event: dict) -> str:
    """Format a raw event dict for display in the feed."""
    event_type = event.get("type", "unknown")

    if event_type == "click":
        text = event.get("text", "")
        selector = event.get("selector", "")
        target = text if text else selector
        return f"[click] {target}"

    elif event_type == "navigate":
        url = event.get("url", "")
        return f"[navigate] {url}"

    elif event_type == "scroll":
        return f"[scroll] scrollY={event.get('scrollY', 0)}"

    elif event_type == "key":
        key = event.get("key", "")
        return f"[key] {key}"

    return f"[{event_type}] {event}"
