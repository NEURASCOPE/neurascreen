"""Selector validator — verify scenario selectors against the real DOM."""

import logging
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar,
)

logger = logging.getLogger("neurascreen.gui")


@dataclass
class SelectorResult:
    """Result of validating one selector."""

    step_index: int
    action: str
    target: str  # selector or text
    target_type: str  # "selector" or "text"
    status: str  # "found", "not_found", "multiple", "skipped"
    matches: int
    suggestion: str  # alternative selector if not_found


def extract_targets(steps: list[dict]) -> list[dict]:
    """Extract validation targets from scenario steps.

    Returns a list of dicts with keys: step_index, action, target, target_type, url.
    """
    targets = []
    current_url = ""

    for i, step in enumerate(steps):
        action = step.get("action", "")

        if action == "navigate":
            current_url = step.get("url", "")
            continue

        if action in ("click", "type", "hover"):
            selector = step.get("selector", "")
            if selector:
                targets.append({
                    "step_index": i,
                    "action": action,
                    "target": selector,
                    "target_type": "selector",
                    "url": current_url,
                })

        elif action == "click_text":
            text = step.get("text", "")
            if text:
                targets.append({
                    "step_index": i,
                    "action": action,
                    "target": text,
                    "target_type": "text",
                    "url": current_url,
                })

    return targets


class ValidatorThread(QThread):
    """Background thread that validates selectors using Playwright."""

    result_ready = Signal(dict)  # one result at a time
    progress = Signal(int, int)  # current, total
    finished_all = Signal(list)  # all results
    error = Signal(str)

    def __init__(self, base_url: str, targets: list[dict], parent=None):
        super().__init__(parent)
        self._base_url = base_url
        self._targets = targets
        self._stop = False

    def run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.error.emit("Playwright not installed")
            return

        results = []
        total = len(self._targets)

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="fr-FR",
                    timezone_id="Europe/Paris",
                )
                page = context.new_page()
                current_url = ""

                for i, target in enumerate(self._targets):
                    if self._stop:
                        break

                    self.progress.emit(i + 1, total)

                    # Navigate if URL changed
                    url = target["url"]
                    if url and url != current_url:
                        full_url = self._base_url.rstrip("/") + url
                        try:
                            page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
                            page.wait_for_timeout(500)
                            current_url = url
                        except Exception:
                            current_url = ""

                    # Validate
                    result = self._validate_one(page, target)
                    results.append(result)
                    self.result_ready.emit(result.__dict__)

                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

        except Exception as e:
            self.error.emit(str(e))
            return

        self.finished_all.emit([r.__dict__ for r in results])

    def stop(self) -> None:
        self._stop = True

    def _validate_one(self, page, target: dict) -> SelectorResult:
        """Validate a single target against the current page."""
        step_index = target["step_index"]
        action = target["action"]
        value = target["target"]
        target_type = target["target_type"]

        try:
            if target_type == "selector":
                elements = page.query_selector_all(value)
                count = len(elements)
                if count == 1:
                    return SelectorResult(step_index, action, value, target_type,
                                          "found", 1, "")
                elif count > 1:
                    return SelectorResult(step_index, action, value, target_type,
                                          "multiple", count, "")
                else:
                    # Try to suggest alternative
                    suggestion = self._suggest_selector(page, value)
                    return SelectorResult(step_index, action, value, target_type,
                                          "not_found", 0, suggestion)

            elif target_type == "text":
                # Look for visible text
                js = """(text) => {
                    const els = document.querySelectorAll('*');
                    let count = 0;
                    for (const el of els) {
                        if (el.innerText && el.innerText.trim().split('\\n')[0].trim() === text
                            && el.offsetParent !== null) {
                            count++;
                        }
                    }
                    return count;
                }"""
                count = page.evaluate(js, value)
                if count == 1:
                    return SelectorResult(step_index, action, value, target_type,
                                          "found", 1, "")
                elif count > 1:
                    return SelectorResult(step_index, action, value, target_type,
                                          "multiple", count, "")
                else:
                    return SelectorResult(step_index, action, value, target_type,
                                          "not_found", 0, "")

        except Exception as e:
            logger.debug("Validation error for step %d: %s", step_index, e)
            return SelectorResult(step_index, action, value, target_type,
                                  "skipped", 0, str(e))

        return SelectorResult(step_index, action, value, target_type,
                              "skipped", 0, "")

    def _suggest_selector(self, page, selector: str) -> str:
        """Try to find a similar selector on the page."""
        # Try relaxing the selector: remove :nth-child, try parent
        parts = selector.split(" > ")
        if len(parts) > 1:
            # Try without the last part
            parent = " > ".join(parts[:-1])
            try:
                count = len(page.query_selector_all(parent))
                if count > 0:
                    return f"Parent found: {parent} ({count} matches)"
            except Exception:
                pass

        # Try by tag name only
        tag = selector.split(".")[0].split("[")[0].split(":")[0].split("#")[0]
        if tag and tag != selector:
            try:
                count = len(page.query_selector_all(tag))
                if count > 0:
                    return f"Tag '{tag}' exists ({count} matches)"
            except Exception:
                pass

        return ""


STATUS_COLORS = {
    "found": "#22C55E",
    "not_found": "#EF4444",
    "multiple": "#F59E0B",
    "skipped": "#64748B",
}

STATUS_ICONS = {
    "found": "\u2713",
    "not_found": "\u2717",
    "multiple": "\u26A0",
    "skipped": "\u2014",
}


class SelectorValidatorDialog(QDialog):
    """Dialog for validating scenario selectors against the real DOM."""

    step_requested = Signal(int)  # double-click → select step in editor

    def __init__(self, steps: list[dict], parent=None, default_url: str = ""):
        super().__init__(parent)
        self._steps = steps
        self._thread: ValidatorThread | None = None

        self.setWindowTitle("Validate Selectors")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)

        self._setup_ui(default_url)

    def _setup_ui(self, default_url: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # URL input
        url_group = QGroupBox("Target Application")
        url_layout = QFormLayout(url_group)
        self._url_input = QLineEdit(default_url)
        self._url_input.setPlaceholderText("http://localhost:8100")
        self._url_input.setMinimumWidth(400)
        url_layout.addRow("Base URL:", self._url_input)
        layout.addWidget(url_group)

        # Controls
        controls = QHBoxLayout()

        targets = extract_targets(self._steps)
        self._target_count = len(targets)
        self._targets_label = QLabel(f"{self._target_count} selectors to validate")
        self._targets_label.setProperty("muted", True)
        controls.addWidget(self._targets_label)
        controls.addStretch()

        self._btn_start = QPushButton("Validate")
        self._btn_start.setProperty("primary", True)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setProperty("danger", True)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        controls.addWidget(self._btn_start)
        controls.addWidget(self._btn_stop)
        layout.addLayout(controls)

        # Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Results table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Step", "Action", "Target", "Status", "Suggestion"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(0, 50)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(1, 80)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(3, 90)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, 1)

        # Summary
        self._summary_label = QLabel("")
        layout.addWidget(self._summary_label)

        # Close
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(btn_close)
        layout.addLayout(close_row)

    def _on_start(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._summary_label.setText("Enter a base URL first")
            return
        if not url.startswith("http"):
            url = "http://" + url

        targets = extract_targets(self._steps)
        if not targets:
            self._summary_label.setText("No selectors to validate")
            return

        self._table.setRowCount(0)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(targets))
        self._progress.setValue(0)
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._summary_label.setText("Validating...")

        self._thread = ValidatorThread(url, targets)
        self._thread.result_ready.connect(self._on_result)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished_all.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_stop(self) -> None:
        if self._thread:
            self._thread.stop()

    def _on_result(self, result: dict) -> None:
        row = self._table.rowCount()
        self._table.setRowCount(row + 1)

        # Step number
        step_item = QTableWidgetItem(str(result["step_index"] + 1))
        step_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        step_item.setData(Qt.ItemDataRole.UserRole, result["step_index"])
        self._table.setItem(row, 0, step_item)

        # Action
        self._table.setItem(row, 1, QTableWidgetItem(result["action"]))

        # Target
        self._table.setItem(row, 2, QTableWidgetItem(result["target"]))

        # Status
        status = result["status"]
        icon = STATUS_ICONS.get(status, "")
        matches = result["matches"]
        status_text = f"{icon} {status}"
        if matches > 1:
            status_text += f" ({matches})"
        status_item = QTableWidgetItem(status_text)
        color = STATUS_COLORS.get(status)
        if color:
            status_item.setForeground(QColor(color))
        self._table.setItem(row, 3, status_item)

        # Suggestion
        self._table.setItem(row, 4, QTableWidgetItem(result.get("suggestion", "")))

    def _on_progress(self, current: int, total: int) -> None:
        self._progress.setValue(current)
        self._summary_label.setText(f"Validating {current}/{total}...")

    def _on_finished(self, results: list[dict]) -> None:
        self._reset_controls()
        counts = {"found": 0, "not_found": 0, "multiple": 0, "skipped": 0}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        self._summary_label.setText(
            f"Done: {counts['found']} found, {counts['not_found']} not found, "
            f"{counts['multiple']} multiple, {counts['skipped']} skipped"
        )

    def _on_error(self, message: str) -> None:
        self._reset_controls()
        self._summary_label.setText(f"Error: {message}")

    def _reset_controls(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.setVisible(False)
        self._thread = None

    def _on_double_click(self, index) -> None:
        row = index.row()
        item = self._table.item(row, 0)
        if item:
            step_index = item.data(Qt.ItemDataRole.UserRole)
            if step_index is not None:
                self.step_requested.emit(step_index)
