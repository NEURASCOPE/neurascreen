"""TTS Panel — dock widget with config, stats, and pronunciation helper."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy,
    QMessageBox, QInputDialog,
)

from ...config import Config
from .stats import NarrationStats, compute_stats
from .pronunciation import (
    Substitution, load_substitutions, save_substitutions,
)
from .audio_preview import AudioPreviewManager
from .voices import (
    ProviderConfig, Voice, PROVIDER_NAMES,
    load_voices, save_voices, add_voice, remove_voice,
    get_provider_help,
)

logger = logging.getLogger("neurascreen.gui")


class TTSPanel(QWidget):
    """TTS configuration, statistics, and pronunciation helper."""

    config_changed = Signal()  # Emitted when TTS config is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_manager = AudioPreviewManager(self)
        self._substitutions: list[Substitution] = []
        self._voice_configs: dict[str, ProviderConfig] = {}
        self._syncing = False

        self._setup_ui()
        self._load_voices()
        self._load_pronunciation()

    @property
    def audio_manager(self) -> AudioPreviewManager:
        return self._audio_manager

    # ------------------------------------------------------------------ #
    #  UI setup                                                           #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        # -- TTS Config --
        config_group = QGroupBox("TTS Configuration")
        config_layout = QGridLayout(config_group)
        config_layout.setSpacing(6)

        # Provider
        config_layout.addWidget(QLabel("Provider:"), 0, 0)
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(PROVIDER_NAMES)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        config_layout.addWidget(self._provider_combo, 0, 1, 1, 2)

        # API Key
        config_layout.addWidget(QLabel("API Key:"), 1, 0)
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("TTS API key")
        config_layout.addWidget(self._api_key_edit, 1, 1, 1, 2)

        # Voice (combo + add/remove buttons)
        # Voice (combo on one row, buttons below)
        config_layout.addWidget(QLabel("Voice:"), 2, 0)
        voice_row = QHBoxLayout()
        voice_row.setSpacing(6)
        self._voice_combo = QComboBox()
        self._voice_combo.setEditable(True)
        self._voice_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        voice_row.addWidget(self._voice_combo)
        self._btn_add_voice = QPushButton("+ Add")
        self._btn_add_voice.setToolTip("Add current voice to saved list")
        self._btn_add_voice.clicked.connect(self._on_add_voice)
        voice_row.addWidget(self._btn_add_voice)
        self._btn_remove_voice = QPushButton("- Del")
        self._btn_remove_voice.setToolTip("Remove selected voice from list")
        self._btn_remove_voice.clicked.connect(self._on_remove_voice)
        voice_row.addWidget(self._btn_remove_voice)
        config_layout.addLayout(voice_row, 2, 1)

        # Model
        config_layout.addWidget(QLabel("Model:"), 3, 0)
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        config_layout.addWidget(self._model_combo, 3, 1)

        # Help label
        self._help_label = QLabel("")
        self._help_label.setProperty("muted", True)
        self._help_label.setWordWrap(True)
        config_layout.addWidget(self._help_label, 4, 0, 1, 2)

        # Test button
        btn_row = QHBoxLayout()
        self._btn_test = QPushButton("Test Connection")
        self._btn_test.clicked.connect(self._on_test_connection)
        btn_row.addWidget(self._btn_test)
        btn_row.addStretch()
        config_layout.addLayout(btn_row, 5, 0, 1, 2)

        layout.addWidget(config_group)

        # -- Stats --
        stats_group = QGroupBox("Narration Statistics")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(4)

        self._lbl_steps = QLabel("0/0 steps narrated")
        self._lbl_words = QLabel("0 words")
        self._lbl_reading = QLabel("~0s reading time")
        self._lbl_total = QLabel("~0s total duration")

        stats_layout.addWidget(QLabel("Steps:"), 0, 0)
        stats_layout.addWidget(self._lbl_steps, 0, 1)
        stats_layout.addWidget(QLabel("Words:"), 1, 0)
        stats_layout.addWidget(self._lbl_words, 1, 1)
        stats_layout.addWidget(QLabel("Reading:"), 2, 0)
        stats_layout.addWidget(self._lbl_reading, 2, 1)
        stats_layout.addWidget(QLabel("Total:"), 3, 0)
        stats_layout.addWidget(self._lbl_total, 3, 1)

        layout.addWidget(stats_group)

        # -- Pronunciation --
        pron_group = QGroupBox("Pronunciation Helper")
        pron_layout = QVBoxLayout(pron_group)
        pron_layout.setSpacing(4)

        self._pron_table = QTableWidget(0, 3)
        self._pron_table.setHorizontalHeaderLabels(["Word", "Replace with", "Reason"])
        self._pron_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self._pron_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self._pron_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._pron_table.verticalHeader().setVisible(False)
        self._pron_table.setAlternatingRowColors(True)
        self._pron_table.cellChanged.connect(self._on_pron_cell_changed)
        pron_layout.addWidget(self._pron_table)

        pron_btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add")
        btn_add.clicked.connect(self._on_pron_add)
        btn_del = QPushButton("Delete")
        btn_del.setProperty("danger", True)
        btn_del.clicked.connect(self._on_pron_delete)
        btn_save = QPushButton("Save")
        btn_save.setProperty("primary", True)
        btn_save.clicked.connect(self._on_pron_save)
        pron_btn_row.addWidget(btn_add)
        pron_btn_row.addWidget(btn_del)
        pron_btn_row.addStretch()
        pron_btn_row.addWidget(btn_save)
        pron_layout.addLayout(pron_btn_row)

        layout.addWidget(pron_group)

        layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Voices                                                             #
    # ------------------------------------------------------------------ #

    def _load_voices(self) -> None:
        """Load voice configs from JSON."""
        self._voice_configs = load_voices()

    def _refresh_voice_combo(self, provider: str) -> None:
        """Refresh voice and model combos for the selected provider."""
        self._syncing = True
        cfg = self._voice_configs.get(provider, ProviderConfig())

        # Voice combo
        self._voice_combo.clear()
        for v in cfg.voices:
            self._voice_combo.addItem(f"{v.name} ({v.id})", v.id)
        # Select default
        if cfg.default_voice:
            for i in range(self._voice_combo.count()):
                if self._voice_combo.itemData(i) == cfg.default_voice:
                    self._voice_combo.setCurrentIndex(i)
                    break

        # Model combo
        self._model_combo.clear()
        if cfg.models:
            self._model_combo.addItems(cfg.models)
        if cfg.default_model:
            idx = self._model_combo.findText(cfg.default_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
            else:
                self._model_combo.setCurrentText(cfg.default_model)

        # Help label
        self._help_label.setText(get_provider_help(provider))

        self._syncing = False

    def _on_provider_changed(self, provider: str) -> None:
        if self._syncing:
            return
        self._refresh_voice_combo(provider)

    def _get_current_voice_id(self) -> str:
        """Get the voice ID from the combo (stored as item data or raw text)."""
        idx = self._voice_combo.currentIndex()
        if idx >= 0:
            data = self._voice_combo.itemData(idx)
            if data:
                return data
        # Fallback to raw text (user typed a custom ID)
        return self._voice_combo.currentText().strip()

    def _on_add_voice(self) -> None:
        """Add a new voice to the current provider."""
        provider = self._provider_combo.currentText()

        voice_id, ok1 = QInputDialog.getText(
            self, "Add Voice", "Voice ID:",
        )
        if not ok1 or not voice_id.strip():
            return

        voice_name, ok2 = QInputDialog.getText(
            self, "Add Voice", "Display name:",
            text=voice_id.strip(),
        )
        if not ok2 or not voice_name.strip():
            return

        if add_voice(self._voice_configs, provider, voice_id.strip(), voice_name.strip()):
            save_voices(self._voice_configs)
            self._refresh_voice_combo(provider)
            # Select the newly added voice
            for i in range(self._voice_combo.count()):
                if self._voice_combo.itemData(i) == voice_id.strip():
                    self._voice_combo.setCurrentIndex(i)
                    break
            logger.info("Added voice '%s' (%s) to %s", voice_name.strip(), voice_id.strip(), provider)
        else:
            QMessageBox.information(self, "Add Voice", "This voice ID already exists.")

    def _on_remove_voice(self) -> None:
        """Remove the selected voice from the current provider."""
        provider = self._provider_combo.currentText()
        voice_id = self._get_current_voice_id()
        if not voice_id:
            return

        result = QMessageBox.question(
            self, "Remove Voice",
            f"Remove voice '{voice_id}' from {provider}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            if remove_voice(self._voice_configs, provider, voice_id):
                save_voices(self._voice_configs)
                self._refresh_voice_combo(provider)
                logger.info("Removed voice '%s' from %s", voice_id, provider)

    # ------------------------------------------------------------------ #
    #  Config                                                             #
    # ------------------------------------------------------------------ #

    def load_config(self, config: Config) -> None:
        """Load TTS settings from a Config object."""
        self._syncing = True
        idx = self._provider_combo.findText(config.tts_provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        else:
            self._provider_combo.setCurrentText(config.tts_provider)
        self._api_key_edit.setText(config.tts_api_key)
        self._syncing = False

        # Refresh combos for this provider
        self._refresh_voice_combo(config.tts_provider)

        # Select the voice from config if it exists
        self._syncing = True
        if config.tts_voice_id:
            found = False
            for i in range(self._voice_combo.count()):
                if self._voice_combo.itemData(i) == config.tts_voice_id:
                    self._voice_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self._voice_combo.setCurrentText(config.tts_voice_id)

        if config.tts_model:
            idx = self._model_combo.findText(config.tts_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
            else:
                self._model_combo.setCurrentText(config.tts_model)
        self._syncing = False

        self._audio_manager.configure(config)

    def get_config_overrides(self) -> dict[str, str]:
        """Return current TTS config values as a dict."""
        return {
            "tts_provider": self._provider_combo.currentText(),
            "tts_api_key": self._api_key_edit.text(),
            "tts_voice_id": self._get_current_voice_id(),
            "tts_model": self._model_combo.currentText(),
        }

    def _build_config(self) -> Config | None:
        """Build a Config from current field values for TTS testing."""
        try:
            overrides = self.get_config_overrides()
            config = Config.load()
            config.tts_provider = overrides["tts_provider"]
            config.tts_api_key = overrides["tts_api_key"]
            config.tts_voice_id = overrides["tts_voice_id"]
            config.tts_model = overrides["tts_model"]
            return config
        except Exception as e:
            logger.error("Failed to build config: %s", e)
            return None

    def _on_test_connection(self) -> None:
        """Test TTS connection with a short sample."""
        config = self._build_config()
        if not config:
            QMessageBox.warning(self, "TTS Error", "Failed to build configuration.")
            return

        errors = config.validate_tts()
        if errors:
            QMessageBox.warning(
                self, "TTS Validation",
                "Fix these errors:\n\n" + "\n".join(f"  - {e}" for e in errors),
            )
            return

        self._audio_manager.configure(config)
        self._btn_test.setText("Generating...")
        self._btn_test.setEnabled(False)

        self._audio_manager.preview_ready.connect(self._on_test_success)
        self._audio_manager.preview_error.connect(self._on_test_error)
        self._audio_manager.test_connection()

    def _on_test_success(self, step_index: int, duration_ms: int) -> None:
        if step_index != -1:
            return
        self._btn_test.setText("Test Connection")
        self._btn_test.setEnabled(True)
        self._audio_manager.preview_ready.disconnect(self._on_test_success)
        self._audio_manager.preview_error.disconnect(self._on_test_error)
        QMessageBox.information(
            self, "TTS Test",
            f"Connection successful.\nAudio duration: {duration_ms}ms",
        )

    def _on_test_error(self, step_index: int, error_msg: str) -> None:
        if step_index != -1:
            return
        self._btn_test.setText("Test Connection")
        self._btn_test.setEnabled(True)
        self._audio_manager.preview_ready.disconnect(self._on_test_success)
        self._audio_manager.preview_error.disconnect(self._on_test_error)
        QMessageBox.critical(self, "TTS Error", f"Connection failed:\n{error_msg}")

    # ------------------------------------------------------------------ #
    #  Stats                                                              #
    # ------------------------------------------------------------------ #

    def update_stats(self, steps: list[dict]) -> None:
        """Recompute and display narration statistics."""
        stats = compute_stats(steps)
        self._lbl_steps.setText(stats.narrated_ratio)
        self._lbl_words.setText(f"{stats.word_count} words")
        self._lbl_reading.setText(f"~{stats.format_duration(stats.estimated_reading_ms)}")
        self._lbl_total.setText(f"~{stats.format_duration(stats.estimated_reading_ms + stats.total_wait_ms)}")

    # ------------------------------------------------------------------ #
    #  Pronunciation                                                      #
    # ------------------------------------------------------------------ #

    def _load_pronunciation(self) -> None:
        """Load pronunciation substitutions into the table."""
        self._substitutions = load_substitutions()
        self._refresh_pron_table()

    def _refresh_pron_table(self) -> None:
        self._syncing = True
        self._pron_table.setRowCount(len(self._substitutions))
        for i, sub in enumerate(self._substitutions):
            self._pron_table.setItem(i, 0, QTableWidgetItem(sub.word))
            self._pron_table.setItem(i, 1, QTableWidgetItem(sub.replacement))
            self._pron_table.setItem(i, 2, QTableWidgetItem(sub.reason))
        self._syncing = False

    def _on_pron_cell_changed(self, row: int, col: int) -> None:
        if self._syncing or row >= len(self._substitutions):
            return
        item = self._pron_table.item(row, col)
        if not item:
            return
        val = item.text()
        sub = self._substitutions[row]
        if col == 0:
            sub.word = val
        elif col == 1:
            sub.replacement = val
        elif col == 2:
            sub.reason = val

    def _on_pron_add(self) -> None:
        self._substitutions.append(Substitution("", "", ""))
        self._refresh_pron_table()
        last = len(self._substitutions) - 1
        self._pron_table.setCurrentCell(last, 0)
        self._pron_table.editItem(self._pron_table.item(last, 0))

    def _on_pron_delete(self) -> None:
        rows = sorted(set(item.row() for item in self._pron_table.selectedItems()), reverse=True)
        for row in rows:
            if 0 <= row < len(self._substitutions):
                self._substitutions.pop(row)
        self._refresh_pron_table()

    def _on_pron_save(self) -> None:
        save_substitutions(self._substitutions)
        logger.info("Pronunciation table saved (%d entries)", len(self._substitutions))

    def get_substitutions(self) -> list[Substitution]:
        return list(self._substitutions)
