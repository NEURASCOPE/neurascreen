"""Autosave and recovery for scenario editing."""

import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger("neurascreen.gui")

# Autosave directory
AUTOSAVE_DIR = Path.home() / ".neurascreen" / "autosave"

# Autosave interval in milliseconds
AUTOSAVE_INTERVAL_MS = 60_000  # 60 seconds


def autosave_path() -> Path:
    """Return the autosave file path."""
    return AUTOSAVE_DIR / "autosave_scenario.json"


def has_recovery() -> bool:
    """Check if an autosave file exists for recovery."""
    return autosave_path().exists()


def save_autosave(scenario: dict) -> None:
    """Write scenario data to the autosave file."""
    AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
    path = autosave_path()
    data = {
        "timestamp": int(time.time()),
        "scenario": scenario,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug("Autosaved to %s", path)


def load_autosave() -> dict | None:
    """Load the autosaved scenario, or None if not found."""
    path = autosave_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("scenario")
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load autosave: %s", e)
        return None


def autosave_timestamp() -> int:
    """Return the timestamp of the autosave file, or 0."""
    path = autosave_path()
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("timestamp", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def clear_autosave() -> None:
    """Delete the autosave file."""
    path = autosave_path()
    if path.exists():
        path.unlink()
        logger.debug("Autosave cleared")


class AutosaveManager:
    """Manages periodic autosave via QTimer.

    Usage:
        manager = AutosaveManager()
        manager.start(get_scenario_fn)  # starts periodic saving
        manager.stop()  # stops the timer
    """

    def __init__(self, interval_ms: int = AUTOSAVE_INTERVAL_MS):
        self._timer = QTimer()
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._on_timeout)
        self._get_scenario = None

    def start(self, get_scenario_fn) -> None:
        """Start autosaving. get_scenario_fn returns a dict or None."""
        self._get_scenario = get_scenario_fn
        self._timer.start()
        logger.info("Autosave started (every %ds)", self._timer.interval() // 1000)

    def stop(self) -> None:
        """Stop autosaving."""
        self._timer.stop()
        self._get_scenario = None

    def _on_timeout(self) -> None:
        if self._get_scenario is None:
            return
        scenario = self._get_scenario()
        if scenario and scenario.get("steps"):
            save_autosave(scenario)


def prompt_recovery(parent=None) -> dict | None:
    """Show recovery dialog if autosave exists. Returns scenario or None."""
    if not has_recovery():
        return None

    ts = autosave_timestamp()
    if ts:
        from datetime import datetime
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        msg = f"An autosaved scenario was found from {time_str}.\n\nRecover it?"
    else:
        msg = "An autosaved scenario was found.\n\nRecover it?"

    result = QMessageBox.question(
        parent, "Recover Autosave",
        msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )

    if result == QMessageBox.StandardButton.Yes:
        scenario = load_autosave()
        clear_autosave()
        return scenario
    else:
        clear_autosave()
        return None
