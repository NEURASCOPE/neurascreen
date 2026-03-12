"""Configuration dialog — visual .env editor with tabbed interface."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTabWidget, QWidget, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox,
    QSizePolicy,
)

from .config_fields import (
    FIELDS, TABS_ORDER, FieldDef,
    TYPE_URL, TYPE_TEXT, TYPE_PASSWORD, TYPE_BOOL,
    TYPE_INT, TYPE_PATH, TYPE_COMBO, TYPE_SELECTOR,
    get_fields_by_tab, get_defaults, validate_values,
    parse_env_file, build_env_content,
)

logger = logging.getLogger("neurascreen.gui")

LABEL_WIDTH = 120


def _make_label(text: str, tooltip: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(LABEL_WIDTH)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if tooltip:
        lbl.setToolTip(tooltip)
    return lbl


def _make_row(label_text: str, widget: QWidget, tooltip: str = "") -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    lbl = _make_label(label_text, tooltip)
    row.addWidget(lbl)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    if tooltip:
        widget.setToolTip(tooltip)
    row.addWidget(widget)
    return row


class ConfigDialog(QDialog):
    """Visual .env configuration editor."""

    config_saved = Signal()

    def __init__(self, env_path: str | None = None, parent=None):
        super().__init__(parent)
        self._env_path = env_path or self._default_env_path()
        self._dirty = False
        self._syncing = False
        self._widgets: dict[str, QWidget] = {}  # env_key -> widget
        self._toggle_buttons: dict[str, QPushButton] = {}  # env_key -> toggle btn

        self.setWindowTitle("Configuration")
        self.setMinimumSize(700, 500)
        self.resize(780, 580)

        self._setup_ui()
        self._load_from_file()

    @staticmethod
    def _default_env_path() -> str:
        return str(Path(__file__).parent.parent.parent.parent / ".env")

    # ------------------------------------------------------------------ #
    #  UI setup                                                           #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Path indicator
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_label = QLabel("File:")
        path_label.setProperty("muted", True)
        self._path_display = QLabel(self._env_path)
        self._path_display.setProperty("muted", True)
        path_row.addWidget(path_label)
        path_row.addWidget(self._path_display, 1)
        layout.addLayout(path_row)

        # Tab widget
        self._tabs = QTabWidget()
        fields_by_tab = get_fields_by_tab()
        for tab_name in TABS_ORDER:
            tab_fields = fields_by_tab.get(tab_name, [])
            if tab_fields:
                tab_widget = self._build_tab(tab_name, tab_fields)
                self._tabs.addTab(tab_widget, tab_name)
        layout.addWidget(self._tabs, 1)

        # Validation label
        self._validation_label = QLabel("")
        self._validation_label.setWordWrap(True)
        layout.addWidget(self._validation_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_import = QPushButton("Import...")
        self._btn_import.setToolTip("Load configuration from another .env file")
        self._btn_import.clicked.connect(self._on_import)
        btn_layout.addWidget(self._btn_import)

        self._btn_export = QPushButton("Export...")
        self._btn_export.setToolTip("Save configuration to a different .env file")
        self._btn_export.clicked.connect(self._on_export)
        btn_layout.addWidget(self._btn_export)

        btn_layout.addStretch()

        self._btn_reset = QPushButton("Reset to Defaults")
        self._btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(self._btn_reset)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_cancel)

        self._btn_save = QPushButton("Save")
        self._btn_save.setProperty("primary", True)
        self._btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self._btn_save)

        layout.addLayout(btn_layout)

    def _build_tab(self, tab_name: str, fields: list[FieldDef]) -> QWidget:
        """Build a scrollable form for one tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form = QVBoxLayout(container)
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(8)
        form.setAlignment(Qt.AlignmentFlag.AlignTop)

        for field_def in fields:
            widget = self._create_field_widget(field_def)
            self._widgets[field_def.env_key] = widget

            if field_def.field_type == TYPE_BOOL:
                # Checkbox gets special layout (indented, no label row)
                cb_row = QHBoxLayout()
                cb_row.setSpacing(8)
                cb_row.addSpacing(LABEL_WIDTH + 8)
                cb_row.addWidget(widget)
                if field_def.tooltip:
                    widget.setToolTip(field_def.tooltip)
                form.addLayout(cb_row)
            elif field_def.field_type == TYPE_PASSWORD:
                # Password field with toggle button
                pwd_row = self._build_password_row(field_def, widget)
                form.addLayout(pwd_row)
            elif field_def.field_type == TYPE_PATH:
                # Path field with browse button
                path_row = self._build_path_row(field_def, widget)
                form.addLayout(path_row)
            else:
                form.addLayout(_make_row(field_def.label + ":", widget, field_def.tooltip))

        form.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_field_widget(self, field_def: FieldDef) -> QWidget:
        """Create the appropriate widget for a field type."""
        if field_def.field_type == TYPE_BOOL:
            cb = QCheckBox(field_def.label)
            cb.stateChanged.connect(self._on_field_changed)
            return cb

        if field_def.field_type == TYPE_INT:
            spin = QSpinBox()
            spin.setRange(field_def.min_value, field_def.max_value)
            spin.setMinimumWidth(120)
            spin.valueChanged.connect(self._on_field_changed)
            return spin

        if field_def.field_type == TYPE_COMBO:
            combo = QComboBox()
            combo.addItems(field_def.options)
            combo.setEditable(True)
            combo.currentTextChanged.connect(self._on_field_changed)
            return combo

        if field_def.field_type == TYPE_PASSWORD:
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setPlaceholderText(field_def.tooltip.split("\n")[0] if field_def.tooltip else "")
            edit.textChanged.connect(self._on_field_changed)
            return edit

        # URL, text, selector, path — all use QLineEdit
        edit = QLineEdit()
        if field_def.field_type == TYPE_URL:
            edit.setPlaceholderText("https://...")
        elif field_def.field_type == TYPE_SELECTOR:
            edit.setPlaceholderText("CSS selector")
        edit.textChanged.connect(self._on_field_changed)
        return edit

    def _build_password_row(self, field_def: FieldDef, widget: QLineEdit) -> QHBoxLayout:
        """Build a row with password field + visibility toggle."""
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = _make_label(field_def.label + ":", field_def.tooltip)
        row.addWidget(lbl)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if field_def.tooltip:
            widget.setToolTip(field_def.tooltip)
        row.addWidget(widget)

        toggle = QPushButton("Show")
        toggle.setFixedWidth(70)
        toggle.setCheckable(True)
        toggle.toggled.connect(lambda checked, w=widget, b=toggle: self._toggle_password(w, b, checked))
        self._toggle_buttons[field_def.env_key] = toggle
        row.addWidget(toggle)
        return row

    def _build_path_row(self, field_def: FieldDef, widget: QLineEdit) -> QHBoxLayout:
        """Build a row with path field + browse button."""
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = _make_label(field_def.label + ":", field_def.tooltip)
        row.addWidget(lbl)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if field_def.tooltip:
            widget.setToolTip(field_def.tooltip)
        row.addWidget(widget)

        browse = QPushButton("Browse...")
        browse.setFixedWidth(90)
        browse.clicked.connect(lambda _, key=field_def.env_key: self._on_browse(key))
        row.addWidget(browse)
        return row

    @staticmethod
    def _toggle_password(widget: QLineEdit, button: QPushButton, show: bool) -> None:
        widget.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password)
        button.setText("Hide" if show else "Show")

    # ------------------------------------------------------------------ #
    #  Load / Save                                                        #
    # ------------------------------------------------------------------ #

    def _load_from_file(self) -> None:
        """Load values from the .env file into widgets."""
        defaults = get_defaults()
        values = dict(defaults)  # start with defaults

        path = Path(self._env_path)
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                parsed = parse_env_file(content)
                values.update(parsed)
            except OSError as e:
                logger.warning("Failed to read %s: %s", self._env_path, e)

        self._set_values(values)
        self._dirty = False
        self._update_title()

    def _set_values(self, values: dict[str, str]) -> None:
        """Push values dict into all widgets."""
        self._syncing = True
        defaults = get_defaults()

        for field_def in FIELDS:
            val = values.get(field_def.env_key, defaults.get(field_def.env_key, ""))
            widget = self._widgets.get(field_def.env_key)
            if widget is None:
                continue

            if field_def.field_type == TYPE_BOOL:
                widget.setChecked(val.lower() == "true")
            elif field_def.field_type == TYPE_INT:
                try:
                    widget.setValue(int(val))
                except (ValueError, TypeError):
                    widget.setValue(int(defaults.get(field_def.env_key, "0")))
            elif field_def.field_type == TYPE_COMBO:
                idx = widget.findText(val)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText(val)
            else:
                widget.setText(val)

        self._syncing = False
        self._validate()

    def _collect_values(self) -> dict[str, str]:
        """Collect current values from all widgets."""
        values: dict[str, str] = {}

        for field_def in FIELDS:
            widget = self._widgets.get(field_def.env_key)
            if widget is None:
                continue

            if field_def.field_type == TYPE_BOOL:
                values[field_def.env_key] = "true" if widget.isChecked() else "false"
            elif field_def.field_type == TYPE_INT:
                values[field_def.env_key] = str(widget.value())
            elif field_def.field_type == TYPE_COMBO:
                values[field_def.env_key] = widget.currentText()
            else:
                values[field_def.env_key] = widget.text()

        return values

    def _save_to_file(self, path: str | None = None) -> bool:
        """Write current values to .env file."""
        target = path or self._env_path
        values = self._collect_values()

        errors = validate_values(values)
        if errors:
            QMessageBox.warning(
                self, "Validation Error",
                "Cannot save — fix these errors:\n\n" + "\n".join(f"  - {e}" for e in errors),
            )
            return False

        try:
            content = build_env_content(values)
            Path(target).write_text(content, encoding="utf-8")
            logger.info("Configuration saved to %s", target)
            self._dirty = False
            self._update_title()
            return True
        except OSError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Validation                                                         #
    # ------------------------------------------------------------------ #

    def _validate(self) -> list[str]:
        """Validate current values and update the validation label."""
        values = self._collect_values()
        errors = validate_values(values)

        if errors:
            self._validation_label.setText(f"{len(errors)} error(s): {errors[0]}")
            self._validation_label.setProperty("error_label", True)
            self._validation_label.setProperty("success_label", False)
            self._validation_label.style().unpolish(self._validation_label)
            self._validation_label.style().polish(self._validation_label)
            self._validation_label.setToolTip("\n".join(errors))
        else:
            self._validation_label.setText("Configuration valid")
            self._validation_label.setProperty("error_label", False)
            self._validation_label.setProperty("success_label", True)
            self._validation_label.style().unpolish(self._validation_label)
            self._validation_label.style().polish(self._validation_label)
            self._validation_label.setToolTip("")

        return errors

    # ------------------------------------------------------------------ #
    #  Dirty tracking                                                     #
    # ------------------------------------------------------------------ #

    def _on_field_changed(self, *_args) -> None:
        if self._syncing:
            return
        self._dirty = True
        self._update_title()
        self._validate()

    def _update_title(self) -> None:
        title = "Configuration"
        if self._dirty:
            title = "* " + title
        self.setWindowTitle(title)

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ------------------------------------------------------------------ #
    #  Slots                                                              #
    # ------------------------------------------------------------------ #

    def _on_save(self) -> None:
        if self._save_to_file():
            self.config_saved.emit()
            self.accept()

    def _on_reset(self) -> None:
        result = QMessageBox.question(
            self, "Reset to Defaults",
            "Reset all fields to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._set_values(get_defaults())
            self._dirty = True
            self._update_title()

    def _on_import(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration",
            "", "Env files (*.env);;All Files (*)",
        )
        if not filepath:
            return

        try:
            content = Path(filepath).read_text(encoding="utf-8")
            parsed = parse_env_file(content)
            if not parsed:
                QMessageBox.warning(self, "Import", "No configuration found in this file.")
                return
            # Merge imported values with current defaults
            defaults = get_defaults()
            values = dict(defaults)
            values.update(parsed)
            self._set_values(values)
            self._dirty = True
            self._update_title()
            QMessageBox.information(
                self, "Import",
                f"Imported {len(parsed)} value(s) from {Path(filepath).name}",
            )
        except OSError as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read file: {e}")

    def _on_export(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration",
            "neurascreen.env", "Env files (*.env);;All Files (*)",
        )
        if filepath:
            self._save_to_file(filepath)

    def _on_browse(self, env_key: str) -> None:
        widget = self._widgets.get(env_key)
        if not isinstance(widget, QLineEdit):
            return

        current = widget.text().strip()
        start_dir = current if current and Path(current).exists() else ""

        directory = QFileDialog.getExistingDirectory(
            self, f"Select directory for {env_key}",
            start_dir,
        )
        if directory:
            widget.setText(directory)

    # ------------------------------------------------------------------ #
    #  Close guard                                                        #
    # ------------------------------------------------------------------ #

    def reject(self) -> None:
        if self._dirty:
            result = QMessageBox.question(
                self, "Unsaved Changes",
                "Configuration has unsaved changes. Discard?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Cancel:
                return
        super().reject()
