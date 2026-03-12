"""Step detail panel: form that adapts to the selected action type."""

import logging

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QSpinBox, QComboBox,
    QCheckBox, QScrollArea, QFrame, QSizePolicy,
)

from ...scenario import VALID_ACTIONS

logger = logging.getLogger("neurascreen.gui")

# Fields required per action type
ACTION_FIELDS: dict[str, list[str]] = {
    "navigate": ["url"],
    "click": ["selector"],
    "click_text": ["text"],
    "type": ["selector", "text", "delay"],
    "scroll": ["selector", "direction", "amount"],
    "hover": ["selector"],
    "key": ["text"],
    "wait": ["duration"],
    "drag": ["text"],
    "delete_node": [],
    "close_modal": [],
    "zoom_out": ["amount"],
    "fit_view": [],
    "screenshot": [],
}

# Action display colors (for step list)
ACTION_COLORS: dict[str, str] = {
    "navigate": "#3B82F6",
    "click": "#22C55E",
    "click_text": "#22C55E",
    "type": "#A855F7",
    "scroll": "#64748B",
    "hover": "#64748B",
    "key": "#F59E0B",
    "wait": "#F59E0B",
    "drag": "#EF4444",
    "delete_node": "#EF4444",
    "close_modal": "#64748B",
    "zoom_out": "#64748B",
    "fit_view": "#64748B",
    "screenshot": "#64748B",
}

SCROLL_DIRECTIONS = ["down", "up"]

LABEL_WIDTH = 75


def _make_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(LABEL_WIDTH)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return lbl


def _make_row(label_text: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(_make_label(label_text))
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    row.addWidget(widget)
    return row


class StepDetailPanel(QWidget):
    """Adaptive form for editing a single step's properties."""

    step_changed = Signal(int, dict)  # (step_index, new_data)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index: int = -1
        self._current_data: dict = {}
        self._updating: bool = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._form_widget = QWidget()
        form = QVBoxLayout(self._form_widget)
        form.setContentsMargins(12, 8, 12, 8)
        form.setSpacing(6)
        form.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -- Action + Title --
        self._action_combo = QComboBox()
        self._action_combo.addItems(sorted(VALID_ACTIONS))
        self._action_combo.currentTextChanged.connect(self._on_action_changed)
        form.addLayout(_make_row("Action:", self._action_combo))

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Step title (for logging)")
        self._title_edit.textChanged.connect(self._on_field_changed)
        form.addLayout(_make_row("Title:", self._title_edit))

        # -- Separator --
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        form.addWidget(sep1)

        # -- Parameters (dynamic) --
        self._params_container = QVBoxLayout()
        self._params_container.setSpacing(6)
        form.addLayout(self._params_container)

        # Create all field widgets
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("/path or full URL")
        self._url_edit.textChanged.connect(self._on_field_changed)

        self._selector_edit = QLineEdit()
        self._selector_edit.setPlaceholderText("CSS selector")
        self._selector_edit.textChanged.connect(self._on_field_changed)

        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("Text content")
        self._text_edit.textChanged.connect(self._on_field_changed)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 5000)
        self._delay_spin.setSuffix(" ms")
        self._delay_spin.setValue(50)
        self._delay_spin.valueChanged.connect(self._on_field_changed)

        self._direction_combo = QComboBox()
        self._direction_combo.addItems(SCROLL_DIRECTIONS)
        self._direction_combo.currentTextChanged.connect(self._on_field_changed)

        self._amount_spin = QSpinBox()
        self._amount_spin.setRange(1, 10000)
        self._amount_spin.setValue(300)
        self._amount_spin.valueChanged.connect(self._on_field_changed)

        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(0, 60000)
        self._duration_spin.setSuffix(" ms")
        self._duration_spin.setValue(1000)
        self._duration_spin.valueChanged.connect(self._on_field_changed)

        self._no_params_label = QLabel("No parameters for this action.")
        self._no_params_label.setProperty("muted", True)

        # Store rows for dynamic show/hide
        self._param_rows: dict[str, tuple[QHBoxLayout, QWidget]] = {}

        # -- Separator --
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        form.addWidget(sep2)

        # -- Options --
        self._wait_spin = QSpinBox()
        self._wait_spin.setRange(0, 60000)
        self._wait_spin.setSuffix(" ms")
        self._wait_spin.setValue(1000)
        self._wait_spin.valueChanged.connect(self._on_field_changed)
        form.addLayout(_make_row("Wait after:", self._wait_spin))

        self._narration_edit = QTextEdit()
        self._narration_edit.setPlaceholderText("Narration text (TTS)")
        self._narration_edit.setMinimumHeight(60)
        self._narration_edit.setMaximumHeight(100)
        self._narration_edit.textChanged.connect(self._on_field_changed)
        narr_row = QHBoxLayout()
        narr_row.setSpacing(8)
        narr_row.addWidget(_make_label("Narration:"), 0, Qt.AlignmentFlag.AlignTop)
        self._narration_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        narr_row.addWidget(self._narration_edit)
        form.addLayout(narr_row)

        self._screenshot_cb = QCheckBox("Screenshot after step")
        self._screenshot_cb.stateChanged.connect(self._on_field_changed)
        cb_row = QHBoxLayout()
        cb_row.setSpacing(8)
        cb_row.addSpacing(LABEL_WIDTH + 8)
        cb_row.addWidget(self._screenshot_cb)
        form.addLayout(cb_row)

        form.addStretch()

        scroll.setWidget(self._form_widget)
        layout.addWidget(scroll)

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self._form_widget.setEnabled(False)

    def load_step(self, index: int, data: dict) -> None:
        self._updating = True
        self._current_index = index
        self._current_data = data.copy()
        self._form_widget.setEnabled(True)

        self._title_edit.setText(data.get("title", ""))

        action = data.get("action", "wait")
        idx = self._action_combo.findText(action)
        if idx >= 0:
            self._action_combo.setCurrentIndex(idx)

        self._url_edit.setText(data.get("url", ""))
        self._selector_edit.setText(data.get("selector", ""))
        self._text_edit.setText(data.get("text", ""))
        self._delay_spin.setValue(data.get("delay", 50))
        dir_val = data.get("direction", "down")
        dir_idx = self._direction_combo.findText(dir_val)
        if dir_idx >= 0:
            self._direction_combo.setCurrentIndex(dir_idx)
        self._amount_spin.setValue(data.get("amount", 300))
        self._duration_spin.setValue(data.get("duration", 1000))
        self._wait_spin.setValue(data.get("wait", 1000))
        self._narration_edit.setPlainText(data.get("narration", ""))
        self._screenshot_cb.setChecked(data.get("screenshot_after", False))

        self._rebuild_action_fields(action)
        self._updating = False

    def _on_action_changed(self, action: str) -> None:
        self._rebuild_action_fields(action)
        if not self._updating:
            self._on_field_changed()

    def _rebuild_action_fields(self, action: str) -> None:
        # Clear params container
        while self._params_container.count() > 0:
            item = self._params_container.takeAt(0)
            if item.layout():
                # Hide widgets in the layout
                for i in range(item.layout().count()):
                    w = item.layout().itemAt(i).widget()
                    if w:
                        w.hide()

        fields = ACTION_FIELDS.get(action, [])

        if not fields:
            self._no_params_label.show()
            row = QHBoxLayout()
            row.addWidget(self._no_params_label)
            self._params_container.addLayout(row)
            return

        self._no_params_label.hide()

        if "url" in fields:
            self._url_edit.show()
            self._params_container.addLayout(_make_row("URL:", self._url_edit))

        if "selector" in fields:
            self._selector_edit.show()
            self._params_container.addLayout(_make_row("Selector:", self._selector_edit))

        if "text" in fields:
            label = "Key:" if action == "key" else "Item:" if action == "drag" else "Text:"
            self._text_edit.show()
            self._params_container.addLayout(_make_row(label, self._text_edit))

        if "delay" in fields:
            self._delay_spin.show()
            self._params_container.addLayout(_make_row("Type delay:", self._delay_spin))

        if "direction" in fields:
            self._direction_combo.show()
            self._params_container.addLayout(_make_row("Direction:", self._direction_combo))

        if "amount" in fields:
            label = "Zoom clicks:" if action == "zoom_out" else "Pixels:"
            self._amount_spin.show()
            self._params_container.addLayout(_make_row(label, self._amount_spin))

        if "duration" in fields:
            self._duration_spin.show()
            self._params_container.addLayout(_make_row("Duration:", self._duration_spin))

    def _on_field_changed(self, *_args) -> None:
        if self._updating or self._current_index < 0:
            return
        data = self._collect_data()
        self.step_changed.emit(self._current_index, data)

    def _collect_data(self) -> dict:
        action = self._action_combo.currentText()
        data: dict = {"action": action}

        title = self._title_edit.text().strip()
        if title:
            data["title"] = title

        fields = ACTION_FIELDS.get(action, [])

        if "url" in fields:
            val = self._url_edit.text().strip()
            if val:
                data["url"] = val

        if "selector" in fields:
            val = self._selector_edit.text().strip()
            if val:
                data["selector"] = val

        if "text" in fields:
            val = self._text_edit.text().strip()
            if val:
                data["text"] = val

        if "delay" in fields:
            val = self._delay_spin.value()
            if val != 50:
                data["delay"] = val

        if "direction" in fields:
            data["direction"] = self._direction_combo.currentText()

        if "amount" in fields:
            val = self._amount_spin.value()
            if val != 300:
                data["amount"] = val

        if "duration" in fields:
            data["duration"] = self._duration_spin.value()

        wait = self._wait_spin.value()
        if wait != 1000:
            data["wait"] = wait

        narration = self._narration_edit.toPlainText().strip()
        if narration:
            data["narration"] = narration

        if self._screenshot_cb.isChecked():
            data["screenshot_after"] = True

        return data

    def clear(self) -> None:
        self._current_index = -1
        self._current_data = {}
        self._updating = True
        self._title_edit.clear()
        self._action_combo.setCurrentIndex(0)
        self._url_edit.clear()
        self._selector_edit.clear()
        self._text_edit.clear()
        self._narration_edit.clear()
        self._screenshot_cb.setChecked(False)
        self._wait_spin.setValue(1000)
        self._duration_spin.setValue(1000)
        self._delay_spin.setValue(50)
        self._amount_spin.setValue(300)
        self._updating = False
        self._show_placeholder()
