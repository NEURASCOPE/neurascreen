"""Step list widget: table showing all steps with drag-reorder."""

import logging

from PySide6.QtCore import Signal, Qt, QMimeData
from PySide6.QtGui import QColor, QDrag
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QMenu,
)

from .step_detail import ACTION_COLORS

logger = logging.getLogger("neurascreen.gui")

# Column indices
COL_NUM = 0
COL_ACTION = 1
COL_TITLE = 2
COL_NARRATION = 3
NUM_COLS = 4


class StepListWidget(QWidget):
    """Table of scenario steps with selection, reorder, and context menu."""

    step_selected = Signal(int)  # index
    steps_reordered = Signal(int, int)  # from_index, to_index
    request_add = Signal(int)  # insert at index
    request_delete = Signal(list)  # list of indices
    request_duplicate = Signal(int)  # index
    request_move_up = Signal(int)
    request_move_down = Signal(int)
    request_insert_template = Signal(int, str)  # index, template_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Table
        self._table = QTableWidget(0, NUM_COLS)
        self._table.setHorizontalHeaderLabels(["#", "Action", "Title", "Narration"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.currentCellChanged.connect(self._on_selection_changed)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_NUM, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_NUM, 40)
        header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_ACTION, 100)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(COL_TITLE, 180)
        header.setSectionResizeMode(COL_NARRATION, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)

        self._btn_add = QPushButton("+ Add")
        self._btn_add.setToolTip("Add a new step")
        self._btn_add.clicked.connect(lambda: self.request_add.emit(self._current_insert_index()))

        self._btn_dup = QPushButton("Dup")
        self._btn_dup.setToolTip("Duplicate selected step")
        self._btn_dup.clicked.connect(self._on_duplicate)

        self._btn_del = QPushButton("Del")
        self._btn_del.setToolTip("Delete selected step(s)")
        self._btn_del.setProperty("danger", True)
        self._btn_del.clicked.connect(self._on_delete)

        self._btn_up = QPushButton("Up")
        self._btn_up.setToolTip("Move step up")
        self._btn_up.clicked.connect(self._on_move_up)

        self._btn_down = QPushButton("Down")
        self._btn_down.setToolTip("Move step down")
        self._btn_down.clicked.connect(self._on_move_down)

        btn_layout.addWidget(self._btn_add)
        btn_layout.addWidget(self._btn_dup)
        btn_layout.addWidget(self._btn_del)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_up)
        btn_layout.addWidget(self._btn_down)

        layout.addLayout(btn_layout)

    def load_steps(self, steps: list[dict]) -> None:
        """Populate the table from a list of step dicts."""
        self._steps = steps
        self.refresh()

    def refresh(self) -> None:
        """Rebuild table rows from current steps data."""
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._steps))

        for i, step in enumerate(self._steps):
            action = step.get("action", "?")
            title = step.get("title", "")
            narration = step.get("narration", "")
            if len(narration) > 60:
                narration = narration[:57] + "..."

            # Number
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, COL_NUM, num_item)

            # Action (colored)
            action_item = QTableWidgetItem(action)
            color = ACTION_COLORS.get(action, "#94A3B8")
            action_item.setForeground(QColor(color))
            self._table.setItem(i, COL_ACTION, action_item)

            # Title
            title_item = QTableWidgetItem(title)
            self._table.setItem(i, COL_TITLE, title_item)

            # Narration preview
            narration_item = QTableWidgetItem(narration)
            if narration:
                narration_item.setForeground(QColor("#F59E0B"))
            self._table.setItem(i, COL_NARRATION, narration_item)

    def selected_indices(self) -> list[int]:
        """Return sorted list of selected row indices."""
        rows = set()
        for item in self._table.selectedItems():
            rows.add(item.row())
        return sorted(rows)

    def select_row(self, index: int) -> None:
        """Select a specific row."""
        if 0 <= index < self._table.rowCount():
            self._table.selectRow(index)

    def _current_insert_index(self) -> int:
        """Index where a new step should be inserted."""
        indices = self.selected_indices()
        if indices:
            return indices[-1] + 1
        return len(self._steps)

    def _on_selection_changed(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        if row >= 0:
            self.step_selected.emit(row)

    def _on_duplicate(self) -> None:
        indices = self.selected_indices()
        if indices:
            self.request_duplicate.emit(indices[0])

    def _on_delete(self) -> None:
        indices = self.selected_indices()
        if indices:
            self.request_delete.emit(indices)

    def _on_move_up(self) -> None:
        indices = self.selected_indices()
        if indices and indices[0] > 0:
            self.request_move_up.emit(indices[0])

    def _on_move_down(self) -> None:
        indices = self.selected_indices()
        if indices and indices[0] < len(self._steps) - 1:
            self.request_move_down.emit(indices[0])

    def _on_context_menu(self, pos) -> None:
        """Show context menu on right-click."""
        menu = QMenu(self)
        indices = self.selected_indices()
        insert_idx = self._current_insert_index()

        menu.addAction("Add step", lambda: self.request_add.emit(insert_idx))

        if indices:
            menu.addAction("Duplicate", lambda: self.request_duplicate.emit(indices[0]))
            menu.addAction("Delete", lambda: self.request_delete.emit(indices))
            menu.addSeparator()
            if indices[0] > 0:
                menu.addAction("Move up", lambda: self.request_move_up.emit(indices[0]))
            if indices[0] < len(self._steps) - 1:
                menu.addAction("Move down", lambda: self.request_move_down.emit(indices[0]))

        menu.addSeparator()

        # Templates submenu
        from .step_templates import get_template_names
        tmpl_menu = menu.addMenu("Insert template")
        for name in get_template_names():
            tmpl_menu.addAction(name, lambda n=name: self.request_insert_template.emit(insert_idx, n))

        menu.exec(self._table.viewport().mapToGlobal(pos))
