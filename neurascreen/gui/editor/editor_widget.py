"""Main scenario editor widget: assembles step list, detail panel, and JSON view."""

import json
import logging
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QFormLayout, QLineEdit, QSpinBox, QGroupBox, QLabel,
    QFileDialog, QMessageBox,
)

from .step_list import StepListWidget
from .step_detail import StepDetailPanel
from .json_view import JsonView
from .step_templates import get_template_steps
from .undo_commands import (
    AddStepCommand, DeleteStepCommand, EditStepCommand,
    MoveStepCommand, BulkDeleteCommand,
)
from ...scenario import validate_scenario

logger = logging.getLogger("neurascreen.gui")


class EditorWidget(QWidget):
    """Complete scenario editor with visual and JSON views."""

    dirty_changed = Signal(bool)  # True when unsaved changes
    title_changed = Signal(str)  # scenario title changed
    file_changed = Signal(str)  # file path changed

    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self._file_path: str = ""
        self._dirty: bool = False
        self._syncing: bool = False
        self._dark = dark

        # Scenario data (mutable, shared with undo commands)
        self._metadata: dict = {
            "title": "",
            "description": "",
            "resolution": {"width": 1920, "height": 1080},
        }
        self._steps: list[dict] = []
        self._selectors: dict = {}

        # Undo stack
        self._undo_stack = QUndoStack(self)
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)

        self._setup_ui()

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ------------------------------------------------------------------ #
    #  UI setup                                                           #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)

        # Metadata bar — compact horizontal layout
        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(8, 6, 8, 6)
        meta_layout.setSpacing(8)

        meta_layout.addWidget(QLabel("Title:"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Scenario title")
        self._title_edit.setMinimumWidth(180)
        self._title_edit.textChanged.connect(self._on_metadata_title_changed)
        meta_layout.addWidget(self._title_edit, 2)

        meta_layout.addWidget(QLabel("Desc:"))
        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Short description")
        self._desc_edit.textChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self._desc_edit, 2)

        meta_layout.addWidget(QLabel("Res:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(320, 7680)
        self._width_spin.setValue(1920)
        self._width_spin.setFixedWidth(70)
        self._width_spin.valueChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self._width_spin)
        meta_layout.addWidget(QLabel("x"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(240, 4320)
        self._height_spin.setValue(1080)
        self._height_spin.setFixedWidth(70)
        self._height_spin.valueChanged.connect(self._on_metadata_changed)
        meta_layout.addWidget(self._height_spin)

        layout.addWidget(meta_widget)

        # Main splitter: step list + (detail | JSON)
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: step list (wrapped with margin)
        self._step_list = StepListWidget()
        self._step_list.step_selected.connect(self._on_step_selected)
        self._step_list.request_add.connect(self._on_add_step)
        self._step_list.request_delete.connect(self._on_delete_steps)
        self._step_list.request_duplicate.connect(self._on_duplicate_step)
        self._step_list.request_move_up.connect(self._on_move_up)
        self._step_list.request_move_down.connect(self._on_move_down)
        self._step_list.request_insert_template.connect(self._on_insert_template)

        step_list_wrapper = QWidget()
        step_list_layout = QVBoxLayout(step_list_wrapper)
        step_list_layout.setContentsMargins(0, 0, 8, 0)
        step_list_layout.addWidget(self._step_list)

        # Right: tabs (Detail | JSON | Split)
        self._right_tabs = QTabWidget()

        # Detail tab
        self._step_detail = StepDetailPanel()
        self._step_detail.step_changed.connect(self._on_step_edited)
        self._right_tabs.addTab(self._step_detail, "Detail")

        # JSON tab
        self._json_view = JsonView(dark=self._dark)
        self._json_view.json_changed.connect(self._on_json_changed)
        self._right_tabs.addTab(self._json_view, "JSON")

        # Split tab (detail left + JSON right)
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        self._split_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._split_detail = StepDetailPanel()
        self._split_detail.step_changed.connect(self._on_step_edited)
        self._split_json = JsonView(dark=self._dark)
        self._split_json.set_read_only(True)
        self._split_splitter.addWidget(self._split_detail)
        self._split_splitter.addWidget(self._split_json)
        self._split_splitter.setSizes([400, 400])
        split_layout.addWidget(self._split_splitter)
        self._right_tabs.addTab(split_widget, "Split")

        self._right_tabs.currentChanged.connect(self._on_tab_changed)

        self._main_splitter.addWidget(step_list_wrapper)
        self._main_splitter.addWidget(self._right_tabs)
        self._main_splitter.setSizes([300, 700])
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 2)

        layout.addWidget(self._main_splitter, 1)

        # Validation bar
        self._validation_label = QLabel("")
        self._validation_label.setProperty("muted", True)
        self._validation_label.setContentsMargins(8, 2, 8, 4)
        self._validation_label.setFixedHeight(22)
        layout.addWidget(self._validation_label)

    # ------------------------------------------------------------------ #
    #  File operations                                                    #
    # ------------------------------------------------------------------ #

    def new_scenario(self) -> None:
        """Create a blank scenario."""
        if self._dirty and not self._confirm_discard():
            return

        self._file_path = ""
        self._metadata = {
            "title": "New Scenario",
            "description": "",
            "resolution": {"width": 1920, "height": 1080},
        }
        self._steps = [{"action": "navigate", "url": "/", "wait": 2000}]
        self._selectors = {}
        self._undo_stack.clear()
        self._load_into_ui()
        self._set_dirty(False)
        self.file_changed.emit("")
        self.title_changed.emit("New Scenario")

    def open_file(self, path: str) -> bool:
        """Load a scenario from a JSON file."""
        if self._dirty and not self._confirm_discard():
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")
            return False

        self._file_path = path
        self._metadata = {
            "title": data.get("title", "Untitled"),
            "description": data.get("description", ""),
            "resolution": data.get("resolution", {"width": 1920, "height": 1080}),
        }
        self._steps = data.get("steps", [])
        self._selectors = data.get("selectors", {})
        self._undo_stack.clear()
        self._load_into_ui()
        self._set_dirty(False)
        self.file_changed.emit(path)
        self.title_changed.emit(self._metadata["title"])
        self._validate()
        logger.info(f"Opened: {path} ({len(self._steps)} steps)")
        return True

    def save(self) -> bool:
        """Save to the current file path."""
        if not self._file_path:
            return self.save_as()
        return self._write_file(self._file_path)

    def save_as(self) -> bool:
        """Save with a file dialog."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario", self._file_path or "scenario.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return False
        if not path.endswith(".json"):
            path += ".json"
        self._file_path = path
        self.file_changed.emit(path)
        return self._write_file(path)

    def _write_file(self, path: str) -> bool:
        """Write current scenario to a file."""
        data = self._build_scenario_dict()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
            return False

        self._undo_stack.setClean()
        self._set_dirty(False)
        logger.info(f"Saved: {path}")
        return True

    def _build_scenario_dict(self) -> dict:
        """Build the full scenario dict from current state."""
        data: dict = {
            "title": self._metadata["title"],
            "description": self._metadata["description"],
            "resolution": self._metadata["resolution"].copy(),
            "steps": [s.copy() for s in self._steps],
        }
        if self._selectors:
            data["selectors"] = self._selectors.copy()
        return data

    def _confirm_discard(self) -> bool:
        """Ask user to confirm discarding unsaved changes."""
        result = QMessageBox.question(
            self, "Unsaved Changes",
            "There are unsaved changes. Discard them?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Save:
            return self.save()
        return result == QMessageBox.StandardButton.Discard

    # ------------------------------------------------------------------ #
    #  UI sync                                                            #
    # ------------------------------------------------------------------ #

    def _load_into_ui(self) -> None:
        """Load current data into all UI widgets."""
        self._syncing = True

        self._title_edit.setText(self._metadata["title"])
        self._desc_edit.setText(self._metadata["description"])
        self._width_spin.setValue(self._metadata["resolution"].get("width", 1920))
        self._height_spin.setValue(self._metadata["resolution"].get("height", 1080))

        self._step_list.load_steps(self._steps)
        self._step_detail.clear()

        self._sync_json_views()
        self._validate()

        self._syncing = False

    def _sync_json_views(self) -> None:
        """Update JSON views from current data."""
        data = self._build_scenario_dict()
        self._json_view.load_scenario(data)
        self._split_json.load_scenario(data)

    def _refresh_after_undo(self) -> None:
        """Refresh UI after an undo/redo operation."""
        self._syncing = True
        selected = self._step_list.selected_indices()
        self._step_list.load_steps(self._steps)
        if selected:
            idx = min(selected[0], len(self._steps) - 1)
            if idx >= 0:
                self._step_list.select_row(idx)
                self._step_detail.load_step(idx, self._steps[idx])
                self._split_detail.load_step(idx, self._steps[idx])
        self._sync_json_views()
        self._validate()
        self._syncing = False

    # ------------------------------------------------------------------ #
    #  Metadata slots                                                     #
    # ------------------------------------------------------------------ #

    def _on_metadata_title_changed(self, text: str) -> None:
        if self._syncing:
            return
        self._metadata["title"] = text
        self._set_dirty(True)
        self.title_changed.emit(text)

    def _on_metadata_changed(self) -> None:
        if self._syncing:
            return
        self._metadata["description"] = self._desc_edit.text()
        self._metadata["resolution"] = {
            "width": self._width_spin.value(),
            "height": self._height_spin.value(),
        }
        self._set_dirty(True)
        self._sync_json_views()

    # ------------------------------------------------------------------ #
    #  Step editing slots                                                 #
    # ------------------------------------------------------------------ #

    def _on_step_selected(self, index: int) -> None:
        """Load selected step into detail panels."""
        if 0 <= index < len(self._steps):
            self._step_detail.load_step(index, self._steps[index])
            self._split_detail.load_step(index, self._steps[index])

    def _on_step_edited(self, index: int, new_data: dict) -> None:
        """Handle step edit from detail panel."""
        if self._syncing or index < 0 or index >= len(self._steps):
            return
        if self._steps[index] == new_data:
            return
        cmd = EditStepCommand(self._steps, index, new_data, f"Edit step {index + 1}")
        self._undo_stack.push(cmd)
        self._refresh_after_undo()
        self._set_dirty(True)

    def _on_add_step(self, index: int) -> None:
        """Add a new empty step at the given index."""
        new_step = {"action": "wait", "duration": 1000, "narration": ""}
        cmd = AddStepCommand(self._steps, index, new_step, "Add step")
        self._undo_stack.push(cmd)
        self._refresh_after_undo()
        self._step_list.select_row(index)
        self._set_dirty(True)

    def _on_delete_steps(self, indices: list[int]) -> None:
        """Delete steps at the given indices."""
        if len(indices) == 1:
            cmd = DeleteStepCommand(self._steps, indices[0], f"Delete step {indices[0] + 1}")
        else:
            cmd = BulkDeleteCommand(self._steps, indices, f"Delete {len(indices)} steps")
        self._undo_stack.push(cmd)
        self._refresh_after_undo()
        self._step_detail.clear()
        self._split_detail.clear()
        self._set_dirty(True)

    def _on_duplicate_step(self, index: int) -> None:
        """Duplicate step at the given index."""
        if 0 <= index < len(self._steps):
            dup = self._steps[index].copy()
            cmd = AddStepCommand(self._steps, index + 1, dup, f"Duplicate step {index + 1}")
            self._undo_stack.push(cmd)
            self._refresh_after_undo()
            self._step_list.select_row(index + 1)
            self._set_dirty(True)

    def _on_move_up(self, index: int) -> None:
        """Move step up."""
        if index > 0:
            cmd = MoveStepCommand(self._steps, index, index - 1, f"Move step {index + 1} up")
            self._undo_stack.push(cmd)
            self._refresh_after_undo()
            self._step_list.select_row(index - 1)
            self._set_dirty(True)

    def _on_move_down(self, index: int) -> None:
        """Move step down."""
        if index < len(self._steps) - 1:
            cmd = MoveStepCommand(self._steps, index, index + 1, f"Move step {index + 1} down")
            self._undo_stack.push(cmd)
            self._refresh_after_undo()
            self._step_list.select_row(index + 1)
            self._set_dirty(True)

    def _on_insert_template(self, index: int, template_name: str) -> None:
        """Insert template steps at the given index."""
        steps = get_template_steps(template_name)
        if not steps:
            return
        # Insert all steps as a single undo group
        self._undo_stack.beginMacro(f"Insert template: {template_name}")
        for i, step in enumerate(steps):
            cmd = AddStepCommand(self._steps, index + i, step)
            self._undo_stack.push(cmd)
        self._undo_stack.endMacro()
        self._refresh_after_undo()
        self._step_list.select_row(index)
        self._set_dirty(True)

    # ------------------------------------------------------------------ #
    #  JSON sync                                                          #
    # ------------------------------------------------------------------ #

    def _on_json_changed(self, data: dict) -> None:
        """Handle JSON edit from the source view."""
        if self._syncing:
            return

        self._syncing = True

        # Update metadata
        self._metadata["title"] = data.get("title", "")
        self._metadata["description"] = data.get("description", "")
        self._metadata["resolution"] = data.get("resolution", {"width": 1920, "height": 1080})
        self._selectors = data.get("selectors", {})

        # Update steps
        self._steps.clear()
        self._steps.extend(data.get("steps", []))

        # Refresh visual widgets
        self._title_edit.setText(self._metadata["title"])
        self._desc_edit.setText(self._metadata["description"])
        self._width_spin.setValue(self._metadata["resolution"].get("width", 1920))
        self._height_spin.setValue(self._metadata["resolution"].get("height", 1080))

        self._step_list.load_steps(self._steps)
        self._step_detail.clear()
        self._split_detail.clear()
        self._split_json.load_scenario(data)

        self._validate()
        self._set_dirty(True)
        self._syncing = False

    def _on_tab_changed(self, index: int) -> None:
        """Sync views when switching tabs."""
        if self._syncing:
            return
        # Refresh JSON views when switching to JSON or Split tab
        if index in (1, 2):
            self._sync_json_views()

    # ------------------------------------------------------------------ #
    #  Validation                                                         #
    # ------------------------------------------------------------------ #

    def _validate(self) -> None:
        """Run validation and update the status label."""
        data = self._build_scenario_dict()
        errors = validate_scenario(data)
        if errors:
            self._validation_label.setText(f"\u26A0 {len(errors)} error(s)")
            self._validation_label.setStyleSheet("color: #EF4444;")
            self._validation_label.setToolTip("\n".join(f"- {e}" for e in errors))
        else:
            count = len(self._steps)
            narrated = sum(1 for s in self._steps if s.get("narration", "").strip())
            self._validation_label.setText(f"\u2713 Valid ({count} steps, {narrated} narrated)")
            self._validation_label.setStyleSheet("color: #22C55E;")
            self._validation_label.setToolTip("")

    # ------------------------------------------------------------------ #
    #  Dirty state                                                        #
    # ------------------------------------------------------------------ #

    def _set_dirty(self, dirty: bool) -> None:
        if self._dirty != dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)

    def _on_clean_changed(self, clean: bool) -> None:
        self._set_dirty(not clean)

    # ------------------------------------------------------------------ #
    #  Clipboard                                                          #
    # ------------------------------------------------------------------ #

    def copy_steps(self) -> None:
        """Copy selected steps to clipboard as JSON."""
        from PySide6.QtWidgets import QApplication
        indices = self._step_list.selected_indices()
        if not indices:
            return
        steps = [self._steps[i].copy() for i in indices]
        text = json.dumps(steps, indent=2, ensure_ascii=False)
        QApplication.clipboard().setText(text)

    def paste_steps(self) -> None:
        """Paste steps from clipboard."""
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if not text:
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return

        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return

        index = self._step_list.selected_indices()
        insert_at = (index[-1] + 1) if index else len(self._steps)

        self._undo_stack.beginMacro(f"Paste {len(data)} step(s)")
        for i, step in enumerate(data):
            if isinstance(step, dict) and "action" in step:
                cmd = AddStepCommand(self._steps, insert_at + i, step)
                self._undo_stack.push(cmd)
        self._undo_stack.endMacro()
        self._refresh_after_undo()
        self._set_dirty(True)
