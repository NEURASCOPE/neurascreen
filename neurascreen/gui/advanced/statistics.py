"""Scenario statistics — compute and display metrics."""

import logging
from collections import Counter
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QGridLayout, QPushButton,
)

logger = logging.getLogger("neurascreen.gui")


@dataclass
class ScenarioStats:
    """Computed scenario statistics."""

    total_steps: int = 0
    action_counts: dict[str, int] = field(default_factory=dict)
    narrated_steps: int = 0
    silent_steps: int = 0
    word_count: int = 0
    estimated_duration_ms: int = 0
    unique_urls: list[str] = field(default_factory=list)
    unique_selectors: int = 0


def compute_scenario_stats(steps: list[dict]) -> ScenarioStats:
    """Compute statistics from a list of step dicts."""
    action_counter: Counter = Counter()
    narrated = 0
    word_count = 0
    total_ms = 0
    urls: set[str] = set()
    selectors: set[str] = set()

    for step in steps:
        action = step.get("action", "unknown")
        action_counter[action] += 1

        narration = step.get("narration", "").strip()
        if narration:
            narrated += 1
            word_count += len(narration.split())

        total_ms += step.get("wait", 0) + step.get("duration", 0)

        url = step.get("url", "")
        if url:
            urls.add(url)

        selector = step.get("selector", "")
        if selector:
            selectors.add(selector)

    # Add estimated reading time (130 wpm)
    if word_count > 0:
        total_ms += int((word_count / 130) * 60 * 1000)

    return ScenarioStats(
        total_steps=len(steps),
        action_counts=dict(action_counter.most_common()),
        narrated_steps=narrated,
        silent_steps=len(steps) - narrated,
        word_count=word_count,
        estimated_duration_ms=total_ms,
        unique_urls=sorted(urls),
        unique_selectors=len(selectors),
    )


def format_duration(ms: int) -> str:
    """Format milliseconds to human-readable duration."""
    s = ms / 1000
    minutes = int(s // 60)
    seconds = int(s % 60)
    if minutes > 0:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


class StatisticsDialog(QDialog):
    """Dialog showing scenario statistics."""

    def __init__(self, steps: list[dict], title: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scenario Statistics")
        self.setMinimumSize(450, 400)
        self.resize(500, 500)

        stats = compute_scenario_stats(steps)
        self._setup_ui(stats, title)

    def _setup_ui(self, stats: ScenarioStats, title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        if title:
            header = QLabel(title)
            header.setProperty("heading", True)
            layout.addWidget(header)

        # Overview
        overview = QGroupBox("Overview")
        grid = QGridLayout(overview)
        grid.setSpacing(8)

        metrics = [
            ("Total steps:", str(stats.total_steps)),
            ("Narrated:", f"{stats.narrated_steps} ({stats.silent_steps} silent)"),
            ("Word count:", str(stats.word_count)),
            ("Estimated duration:", format_duration(stats.estimated_duration_ms)),
            ("Unique URLs:", str(len(stats.unique_urls))),
            ("Unique selectors:", str(stats.unique_selectors)),
        ]
        for row, (label, value) in enumerate(metrics):
            grid.addWidget(QLabel(label), row, 0)
            val_label = QLabel(value)
            val_label.setProperty("subheading", True)
            grid.addWidget(val_label, row, 1)

        layout.addWidget(overview)

        # Actions breakdown
        actions_group = QGroupBox("Actions Breakdown")
        actions_layout = QVBoxLayout(actions_group)

        table = QTableWidget(len(stats.action_counts), 2)
        table.setHorizontalHeaderLabels(["Action", "Count"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().resizeSection(1, 80)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row, (action, count) in enumerate(stats.action_counts.items()):
            table.setItem(row, 0, QTableWidgetItem(action))
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, count_item)

        actions_layout.addWidget(table)
        layout.addWidget(actions_group)

        # URLs
        if stats.unique_urls:
            urls_group = QGroupBox(f"Pages Visited ({len(stats.unique_urls)})")
            urls_layout = QVBoxLayout(urls_group)
            for url in stats.unique_urls:
                urls_layout.addWidget(QLabel(url))
            layout.addWidget(urls_group)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
