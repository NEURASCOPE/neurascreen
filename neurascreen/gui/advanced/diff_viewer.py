"""Scenario diff — compare two scenarios side by side."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFileDialog, QGroupBox,
)

logger = logging.getLogger("neurascreen.gui")


@dataclass
class DiffEntry:
    """A single difference between two scenarios."""

    index: int
    kind: str  # "added", "removed", "modified", "unchanged"
    left: dict | None  # step from scenario A
    right: dict | None  # step from scenario B
    changes: list[str]  # list of changed fields


def diff_steps(steps_a: list[dict], steps_b: list[dict]) -> list[DiffEntry]:
    """Compute a simple positional diff between two step lists.

    This is a positional diff (not LCS-based) — it compares steps
    at the same index and reports additions/removals at the end.
    """
    entries = []
    max_len = max(len(steps_a), len(steps_b))

    for i in range(max_len):
        a = steps_a[i] if i < len(steps_a) else None
        b = steps_b[i] if i < len(steps_b) else None

        if a is None:
            entries.append(DiffEntry(i, "added", None, b, []))
        elif b is None:
            entries.append(DiffEntry(i, "removed", a, None, []))
        elif a == b:
            entries.append(DiffEntry(i, "unchanged", a, b, []))
        else:
            changes = _find_changes(a, b)
            entries.append(DiffEntry(i, "modified", a, b, changes))

    return entries


def diff_summary(entries: list[DiffEntry]) -> dict:
    """Summarize diff entries into counts."""
    counts = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    for e in entries:
        counts[e.kind] += 1
    return counts


def _find_changes(a: dict, b: dict) -> list[str]:
    """List the fields that differ between two step dicts."""
    all_keys = set(a.keys()) | set(b.keys())
    changes = []
    for key in sorted(all_keys):
        val_a = a.get(key)
        val_b = b.get(key)
        if val_a != val_b:
            changes.append(key)
    return changes


DIFF_COLORS = {
    "added": "#22C55E",
    "removed": "#EF4444",
    "modified": "#F59E0B",
    "unchanged": None,
}


class DiffDialog(QDialog):
    """Dialog showing side-by-side scenario diff."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Scenarios")
        self.setMinimumSize(800, 500)
        self.resize(900, 600)

        self._path_a: str = ""
        self._path_b: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # File selection
        files_group = QGroupBox("Files")
        files_layout = QVBoxLayout(files_group)

        row_a = QHBoxLayout()
        self._label_a = QLabel("File A: (none)")
        btn_a = QPushButton("Browse...")
        btn_a.clicked.connect(lambda: self._browse("a"))
        row_a.addWidget(self._label_a, 1)
        row_a.addWidget(btn_a)
        files_layout.addLayout(row_a)

        row_b = QHBoxLayout()
        self._label_b = QLabel("File B: (none)")
        btn_b = QPushButton("Browse...")
        btn_b.clicked.connect(lambda: self._browse("b"))
        row_b.addWidget(self._label_b, 1)
        row_b.addWidget(btn_b)
        files_layout.addLayout(row_b)

        layout.addWidget(files_group)

        # Compare button
        btn_row = QHBoxLayout()
        self._btn_compare = QPushButton("Compare")
        self._btn_compare.setProperty("primary", True)
        self._btn_compare.setEnabled(False)
        self._btn_compare.clicked.connect(self._on_compare)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_compare)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Summary
        self._summary_label = QLabel("")
        self._summary_label.setProperty("muted", True)
        layout.addWidget(self._summary_label)

        # Diff table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["#", "Status", "Action A", "Action B", "Changes"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(0, 40)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(1, 80)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().resizeSection(2, 180)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().resizeSection(3, 180)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, 1)

        # Close
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

    def _browse(self, which: str) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, f"Select Scenario {which.upper()}",
            "", "JSON Scenarios (*.json);;All Files (*)",
        )
        if not filepath:
            return
        if which == "a":
            self._path_a = filepath
            self._label_a.setText(f"File A: {Path(filepath).name}")
        else:
            self._path_b = filepath
            self._label_b.setText(f"File B: {Path(filepath).name}")
        self._btn_compare.setEnabled(bool(self._path_a and self._path_b))

    def _on_compare(self) -> None:
        try:
            with open(self._path_a, "r", encoding="utf-8") as f:
                data_a = json.load(f)
            with open(self._path_b, "r", encoding="utf-8") as f:
                data_b = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._summary_label.setText(f"Error: {e}")
            return

        steps_a = data_a.get("steps", [])
        steps_b = data_b.get("steps", [])
        entries = diff_steps(steps_a, steps_b)
        summary = diff_summary(entries)

        self._summary_label.setText(
            f"{summary['unchanged']} unchanged, "
            f"{summary['modified']} modified, "
            f"{summary['added']} added, "
            f"{summary['removed']} removed"
        )

        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            # Index
            idx_item = QTableWidgetItem(str(entry.index + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, idx_item)

            # Status
            status_item = QTableWidgetItem(entry.kind)
            color = DIFF_COLORS.get(entry.kind)
            if color:
                status_item.setForeground(QColor(color))
            self._table.setItem(row, 1, status_item)

            # Action A
            action_a = entry.left.get("action", "") if entry.left else ""
            title_a = entry.left.get("title", "") if entry.left else ""
            text_a = f"{action_a}: {title_a}" if title_a else action_a
            self._table.setItem(row, 2, QTableWidgetItem(text_a))

            # Action B
            action_b = entry.right.get("action", "") if entry.right else ""
            title_b = entry.right.get("title", "") if entry.right else ""
            text_b = f"{action_b}: {title_b}" if title_b else action_b
            self._table.setItem(row, 3, QTableWidgetItem(text_b))

            # Changes
            changes_text = ", ".join(entry.changes) if entry.changes else ""
            self._table.setItem(row, 4, QTableWidgetItem(changes_text))

    def load_files(self, path_a: str, path_b: str) -> None:
        """Pre-load file paths programmatically."""
        self._path_a = path_a
        self._path_b = path_b
        self._label_a.setText(f"File A: {Path(path_a).name}")
        self._label_b.setText(f"File B: {Path(path_b).name}")
        self._btn_compare.setEnabled(True)
