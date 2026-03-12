"""Macro recorder dialog: record browser interactions and generate scenarios."""

import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel,
    QFileDialog, QGroupBox, QCheckBox,
)

from .event_feed import EventFeed
from .cleanup import cleanup_events, cleanup_steps

logger = logging.getLogger("neurascreen.gui")


class RecorderThread(QThread):
    """Background thread that runs Playwright and captures browser events.

    Communicates with the dialog via signals:
    - event_captured: emitted for each new event (for live feed)
    - recording_finished: emitted when browser closes (with all events)
    - recording_error: emitted on error
    - status_changed: emitted for status updates
    """

    event_captured = Signal(dict)
    recording_finished = Signal(list, list)  # (events, navigations)
    recording_error = Signal(str)
    status_changed = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._stop_requested = False
        self._page = None

    def run(self) -> None:
        """Launch browser, inject capture script, poll for events."""
        try:
            from playwright.sync_api import sync_playwright
            from neurascreen.macro import _CAPTURE_SCRIPT
        except ImportError as e:
            self.recording_error.emit(f"Missing dependency: {e}")
            return

        navigations = []
        last_event_count = 0

        self.status_changed.emit("Launching browser...")

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    locale="fr-FR",
                    timezone_id="Europe/Paris",
                    no_viewport=True,
                )

                page = context.new_page()
                self._page = page

                # Track navigations
                def _on_navigation(frame):
                    if frame == page.main_frame:
                        nav = {
                            "type": "navigate",
                            "timestamp": int(time.time() * 1000),
                            "url": urlparse(page.url).path,
                        }
                        navigations.append(nav)
                        self.event_captured.emit(nav)

                page.on("framenavigated", _on_navigation)

                # Inject capture script
                page.add_init_script(_CAPTURE_SCRIPT)

                self.status_changed.emit("Navigating...")
                page.goto(self._url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                page.evaluate(_CAPTURE_SCRIPT)

                self.status_changed.emit("Recording... Close browser or click Stop.")

                # Poll loop
                while not self._stop_requested:
                    try:
                        # Check if browser is still open
                        page.evaluate("1")
                    except Exception:
                        break

                    # Poll new events
                    try:
                        all_events = page.evaluate(
                            "window.__neurascreen_events || []"
                        )
                        new_count = len(all_events)
                        if new_count > last_event_count:
                            for event in all_events[last_event_count:]:
                                self.event_captured.emit(event)
                            last_event_count = new_count
                    except Exception:
                        pass

                    time.sleep(0.5)

                # Final event collection
                events = []
                try:
                    events = page.evaluate(
                        "window.__neurascreen_events || []"
                    )
                except Exception:
                    pass

                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

                self._page = None
                self.recording_finished.emit(events, navigations)

        except Exception as e:
            self._page = None
            self.recording_error.emit(str(e))

    def stop(self) -> None:
        """Request the recording to stop."""
        self._stop_requested = True
        # Try to close the browser page to break the poll loop faster
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass


class RecorderDialog(QDialog):
    """Dialog for recording browser interactions and generating scenarios.

    Provides:
    - URL and title input
    - Start/Stop recording
    - Live event feed
    - Post-recording cleanup and save
    """

    scenario_ready = Signal(str)  # path to saved scenario file

    def __init__(self, parent=None, default_url: str = ""):
        super().__init__(parent)
        self._thread: RecorderThread | None = None
        self._raw_events: list[dict] = []
        self._navigations: list[dict] = []
        self._steps: list[dict] = []

        self.setWindowTitle("Record Macro")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        self._setup_ui(default_url)

    def _setup_ui(self, default_url: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # -- Setup group --
        setup_group = QGroupBox("Setup")
        setup_layout = QFormLayout(setup_group)

        self._url_input = QLineEdit(default_url)
        self._url_input.setPlaceholderText("https://localhost:8100/customer")
        self._url_input.setMinimumWidth(450)
        setup_layout.addRow("Start URL:", self._url_input)

        self._title_input = QLineEdit("Recorded Scenario")
        self._title_input.setPlaceholderText("Scenario title")
        setup_layout.addRow("Title:", self._title_input)

        layout.addWidget(setup_group)

        # -- Controls --
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._btn_start = QPushButton("Start Recording")
        self._btn_start.setProperty("primary", True)
        self._btn_start.setMinimumWidth(140)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("Stop Recording")
        self._btn_stop.setProperty("danger", True)
        self._btn_stop.setMinimumWidth(140)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        self._status_label = QLabel("Ready")
        self._status_label.setProperty("muted", True)

        controls.addWidget(self._btn_start)
        controls.addWidget(self._btn_stop)
        controls.addStretch()
        controls.addWidget(self._status_label)

        layout.addLayout(controls)

        # -- Event feed --
        self._event_feed = EventFeed()
        layout.addWidget(self._event_feed, 1)

        # -- Cleanup options --
        cleanup_group = QGroupBox("Cleanup Options")
        cleanup_layout = QHBoxLayout(cleanup_group)

        self._cb_dedup = QCheckBox("Dedup clicks")
        self._cb_dedup.setChecked(True)
        self._cb_dedup.setToolTip("Remove duplicate clicks on the same element (<300ms)")

        self._cb_merge_nav = QCheckBox("Merge navigations")
        self._cb_merge_nav.setChecked(True)
        self._cb_merge_nav.setToolTip("Merge consecutive navigation events")

        self._cb_cap_waits = QCheckBox("Cap waits (5s)")
        self._cb_cap_waits.setChecked(True)
        self._cb_cap_waits.setToolTip("Cap wait durations to 5s, remove <500ms")

        cleanup_layout.addWidget(self._cb_dedup)
        cleanup_layout.addWidget(self._cb_merge_nav)
        cleanup_layout.addWidget(self._cb_cap_waits)
        cleanup_layout.addStretch()

        layout.addWidget(cleanup_group)

        # -- Result summary --
        self._result_label = QLabel("")
        self._result_label.setVisible(False)
        layout.addWidget(self._result_label)

        # -- Bottom buttons --
        btn_layout = QHBoxLayout()

        self._btn_open_editor = QPushButton("Open in Editor")
        self._btn_open_editor.setProperty("primary", True)
        self._btn_open_editor.setEnabled(False)
        self._btn_open_editor.clicked.connect(self._on_open_editor)

        self._btn_save = QPushButton("Save as...")
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save)

        self._btn_close = QPushButton("Close")
        self._btn_close.clicked.connect(self.reject)

        btn_layout.addWidget(self._btn_open_editor)
        btn_layout.addWidget(self._btn_save)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------ #
    #  Recording                                                          #
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        """Start recording browser interactions."""
        url = self._url_input.text().strip()
        if not url:
            self._status_label.setText("Enter a URL first")
            return

        # Ensure URL has scheme
        if not url.startswith("http"):
            url = "http://" + url

        self._raw_events.clear()
        self._navigations.clear()
        self._steps.clear()
        self._event_feed.clear()
        self._result_label.setVisible(False)
        self._btn_open_editor.setEnabled(False)
        self._btn_save.setEnabled(False)

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._url_input.setEnabled(False)
        self._title_input.setEnabled(False)

        self._thread = RecorderThread(url)
        self._thread.event_captured.connect(self._on_event)
        self._thread.recording_finished.connect(self._on_finished)
        self._thread.recording_error.connect(self._on_error)
        self._thread.status_changed.connect(self._on_status)
        self._thread.start()

    def _on_stop(self) -> None:
        """Stop recording."""
        if self._thread and self._thread.isRunning():
            self._status_label.setText("Stopping...")
            self._thread.stop()

    def _on_event(self, event: dict) -> None:
        """Handle a captured event (live feed)."""
        self._event_feed.add_event(event)

    def _on_status(self, message: str) -> None:
        """Update status label."""
        self._status_label.setText(message)

    def _on_finished(self, events: list[dict], navigations: list[dict]) -> None:
        """Handle recording completion."""
        self._raw_events = events
        self._navigations = navigations
        self._reset_controls()

        # Apply cleanup and convert to steps
        self._process_recording()

    def _on_error(self, message: str) -> None:
        """Handle recording error."""
        self._reset_controls()
        self._status_label.setText(f"Error: {message}")
        logger.error("Recording error: %s", message)

    def _reset_controls(self) -> None:
        """Re-enable controls after recording ends."""
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._url_input.setEnabled(True)
        self._title_input.setEnabled(True)
        self._thread = None

    # ------------------------------------------------------------------ #
    #  Post-processing                                                    #
    # ------------------------------------------------------------------ #

    def _process_recording(self) -> None:
        """Convert raw events to scenario steps with cleanup."""
        from neurascreen.macro import _events_to_steps

        url = self._url_input.text().strip()

        # Merge navigations + captured events
        all_events = self._navigations + self._raw_events
        all_events.sort(key=lambda e: e.get("timestamp", 0))

        # Apply event-level cleanup
        cleaned = cleanup_events(
            all_events,
            dedup_threshold_ms=300 if self._cb_dedup.isChecked() else 0,
        )

        # Convert to steps
        steps = _events_to_steps(cleaned, url)

        # Apply step-level cleanup
        if self._cb_cap_waits.isChecked():
            steps = cleanup_steps(steps)

        self._steps = steps

        # Show result
        raw_count = len(self._raw_events) + len(self._navigations)
        self._result_label.setText(
            f"Recorded {raw_count} events -> {len(steps)} steps"
        )
        self._result_label.setVisible(True)
        self._status_label.setText("Recording complete")

        if steps:
            self._btn_open_editor.setEnabled(True)
            self._btn_save.setEnabled(True)

    def _build_scenario(self) -> dict:
        """Build a complete scenario dict from recorded steps."""
        return {
            "title": self._title_input.text().strip() or "Recorded Scenario",
            "description": f"Recorded from {self._url_input.text().strip()}",
            "resolution": {"width": 1920, "height": 1080},
            "steps": self._steps,
        }

    # ------------------------------------------------------------------ #
    #  Save / Open in editor                                              #
    # ------------------------------------------------------------------ #

    def _on_save(self) -> None:
        """Save recorded scenario to a JSON file."""
        if not self._steps:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario",
            "",
            "JSON Scenarios (*.json);;All Files (*)",
        )
        if not filepath:
            return

        scenario = self._build_scenario()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        self._status_label.setText(f"Saved: {Path(filepath).name}")
        self._saved_path = filepath

    def _on_open_editor(self) -> None:
        """Save to a temp file and emit signal to open in editor."""
        if not self._steps:
            return

        # Save to temp location
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "recorded_scenario.json"
        scenario = self._build_scenario()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        self.scenario_ready.emit(str(tmp))
        self.accept()

    # ------------------------------------------------------------------ #
    #  Properties for testing                                             #
    # ------------------------------------------------------------------ #

    @property
    def steps(self) -> list[dict]:
        return self._steps

    @property
    def raw_events(self) -> list[dict]:
        return self._raw_events
