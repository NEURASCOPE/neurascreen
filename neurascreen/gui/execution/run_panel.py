"""Execution panel: command selection, options, run/stop, and console."""

import logging
import time

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QCheckBox, QLabel,
    QFrame,
)

from .console import ConsoleWidget
from .runner import CommandRunner

logger = logging.getLogger("neurascreen.gui")


class RunPanel(QWidget):
    """Complete execution panel with command controls and console output."""

    status_changed = Signal(str)  # status bar message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner: CommandRunner | None = None
        self._scenario_path: str = ""
        self._start_time: float = 0.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Controls bar
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 6, 8, 6)
        controls_layout.setSpacing(8)

        # Command selector
        cmd_label = QLabel("Command:")
        self._cmd_combo = QComboBox()
        self._cmd_combo.addItems(["validate", "preview", "run", "full"])
        self._cmd_combo.setCurrentText("validate")
        self._cmd_combo.setMinimumWidth(100)

        controls_layout.addWidget(cmd_label)
        controls_layout.addWidget(self._cmd_combo)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        controls_layout.addWidget(sep1)

        # Options
        self._cb_srt = QCheckBox("SRT")
        self._cb_srt.setToolTip("Generate SRT subtitle file")
        self._cb_chapters = QCheckBox("Chapters")
        self._cb_chapters.setToolTip("Generate YouTube chapter markers")
        self._cb_headless = QCheckBox("Headless")
        self._cb_headless.setToolTip("Run browser in headless mode")
        self._cb_verbose = QCheckBox("Verbose")
        self._cb_verbose.setToolTip("Enable debug logging")

        controls_layout.addWidget(self._cb_srt)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self._cb_chapters)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self._cb_headless)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self._cb_verbose)

        controls_layout.addStretch()

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        controls_layout.addWidget(sep2)

        # Run / Stop buttons
        self._btn_run = QPushButton("Run")
        self._btn_run.setProperty("primary", True)
        self._btn_run.setMinimumWidth(80)
        self._btn_run.clicked.connect(self._on_run)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setProperty("danger", True)
        self._btn_stop.setMinimumWidth(80)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        controls_layout.addWidget(self._btn_run)
        controls_layout.addWidget(self._btn_stop)

        layout.addWidget(controls)

        # Console
        self._console = ConsoleWidget()
        layout.addWidget(self._console)

    @property
    def is_running(self) -> bool:
        return self._runner is not None and self._runner.isRunning()

    def set_scenario_path(self, path: str) -> None:
        """Set the scenario file path for execution."""
        self._scenario_path = path

    def set_command(self, command: str) -> None:
        """Set the command to run."""
        idx = self._cmd_combo.findText(command)
        if idx >= 0:
            self._cmd_combo.setCurrentIndex(idx)

    def run_command(self, command: str, scenario_path: str | None = None) -> None:
        """Programmatically start a command."""
        if command:
            self.set_command(command)
        if scenario_path:
            self._scenario_path = scenario_path
        self._on_run()

    # ------------------------------------------------------------------ #
    #  Slots                                                              #
    # ------------------------------------------------------------------ #

    def _on_run(self) -> None:
        """Start executing the selected command."""
        if self.is_running:
            return

        if not self._scenario_path:
            self._console.append_error("No scenario file. Save or open a scenario first.")
            return

        command = self._cmd_combo.currentText()
        options = {
            "srt": self._cb_srt.isChecked(),
            "chapters": self._cb_chapters.isChecked(),
            "headless": self._cb_headless.isChecked(),
            "verbose": self._cb_verbose.isChecked(),
        }

        self._console.clear()
        self._console.append_info(f"--- {command.upper()} : {self._scenario_path} ---\n")

        self._runner = CommandRunner(command, self._scenario_path, options)
        self._runner.line_output.connect(self._console.append_line)
        self._runner.progress.connect(self._on_progress)
        self._runner.finished_ok.connect(self._on_finished_ok)
        self._runner.finished_error.connect(self._on_finished_error)

        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._cmd_combo.setEnabled(False)
        self._start_time = time.time()

        self.status_changed.emit(f"Running {command}...")
        self._runner.start()

    def _on_stop(self) -> None:
        """Cancel the running command."""
        if self._runner and self._runner.isRunning():
            self._runner.cancel()
            self.status_changed.emit("Cancelling...")

    def _on_progress(self, text: str) -> None:
        """Update status with step progress."""
        self.status_changed.emit(f"Running... {text}")

    def _on_finished_ok(self) -> None:
        """Handle successful completion."""
        elapsed = time.time() - self._start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes}m{seconds:02d}s" if minutes > 0 else f"{seconds}s"

        self._console.append_success(f"\n--- Done in {time_str} ---")
        self.status_changed.emit(f"Done in {time_str}")
        self._reset_buttons()

    def _on_finished_error(self, message: str) -> None:
        """Handle failed completion."""
        self._console.append_error(f"\n--- Failed: {message} ---")
        self.status_changed.emit(f"Failed: {message}")
        self._reset_buttons()

    def _reset_buttons(self) -> None:
        """Re-enable controls after execution."""
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._cmd_combo.setEnabled(True)
        self._runner = None
