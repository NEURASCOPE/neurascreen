"""Main application window."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSplitter, QToolBar,
    QStatusBar, QDockWidget, QFileDialog,
    QMessageBox, QStackedWidget,
    QApplication,
)

from .theme import ThemeEngine
from .editor.editor_widget import EditorWidget
from .editor.file_browser import FileBrowser
from .execution.run_panel import RunPanel

logger = logging.getLogger("neurascreen.gui")

APP_NAME = "NeuraScreen"
ORG_NAME = "NEURASCOPE"
SETTINGS_GEOMETRY = "window/geometry"
SETTINGS_STATE = "window/state"
SETTINGS_THEME = "window/theme"
SETTINGS_RECENT_FILES = "window/recent_files"
MAX_RECENT_FILES = 10


class MainWindow(QMainWindow):
    """NeuraScreen main application window."""

    def __init__(self, theme_engine: ThemeEngine):
        super().__init__()
        self.theme_engine = theme_engine
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self._recent_files: list[str] = []

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1200, 750)

        self._setup_central()
        self._setup_sidebar()
        self._setup_execution_dock()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._connect_editor()
        self._connect_execution()
        self._restore_state()
        self._load_recent_files()
        self._init_sidebar_roots()

        logger.info("Main window initialized")

    # ------------------------------------------------------------------ #
    #  Central area                                                       #
    # ------------------------------------------------------------------ #

    def _setup_central(self) -> None:
        """Set up the central stacked widget with welcome page and editor."""
        self._central_stack = QStackedWidget()
        self._central_stack.setContentsMargins(4, 0, 0, 0)

        # Welcome page
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Automated demo video generator")
        subtitle.setProperty("subheading", True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version_label = QLabel(self._get_version())
        version_label.setProperty("muted", True)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Open a scenario (Ctrl+O) or create a new one (Ctrl+N)")
        hint.setProperty("muted", True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(version_label)
        layout.addSpacing(24)
        layout.addWidget(hint)

        self._welcome_page = welcome
        self._central_stack.addWidget(welcome)  # index 0

        # Editor
        is_dark = self.theme_engine.current.is_dark if self.theme_engine.current else True
        self._editor = EditorWidget(dark=is_dark)
        self._central_stack.addWidget(self._editor)  # index 1

        self.setCentralWidget(self._central_stack)

    # ------------------------------------------------------------------ #
    #  Sidebar                                                            #
    # ------------------------------------------------------------------ #

    def _setup_sidebar(self) -> None:
        """Set up the left sidebar dock with file browser."""
        self._sidebar_dock = QDockWidget("Explorer", self)
        self._sidebar_dock.setObjectName("sidebar")
        self._sidebar_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        self._file_browser = FileBrowser()
        self._file_browser.file_selected.connect(self._open_file)
        self._sidebar_dock.setWidget(self._file_browser)
        self._sidebar_dock.setMinimumWidth(200)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._sidebar_dock)

    def _init_sidebar_roots(self) -> None:
        """Add default scenario directories to the file browser."""
        project_root = Path(__file__).parent.parent.parent
        paths = [
            project_root / "scenarios",
            project_root / "examples",
        ]
        existing = [p for p in paths if p.exists()]
        if existing:
            self._file_browser.set_roots(existing)

    # ------------------------------------------------------------------ #
    #  Execution dock                                                     #
    # ------------------------------------------------------------------ #

    def _setup_execution_dock(self) -> None:
        """Set up the bottom execution panel dock."""
        self._exec_dock = QDockWidget("Console", self)
        self._exec_dock.setObjectName("execution")
        self._exec_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        self._run_panel = RunPanel()
        self._run_panel.status_changed.connect(self.set_status)
        self._exec_dock.setWidget(self._run_panel)
        self._exec_dock.setMinimumHeight(150)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._exec_dock)
        self._exec_dock.hide()

    def _connect_execution(self) -> None:
        """Connect execution actions to the run panel."""
        self._act_validate.triggered.connect(lambda: self._run_command("validate"))
        self._act_preview.triggered.connect(lambda: self._run_command("preview"))
        self._act_run.triggered.connect(lambda: self._run_command("run"))
        self._act_full.triggered.connect(lambda: self._run_command("full"))

    def _run_command(self, command: str) -> None:
        """Launch a command on the current scenario."""
        if self._run_panel.is_running:
            self.set_status("A command is already running")
            return

        # Save first if dirty
        if self._editor.is_dirty:
            if not self._editor.save():
                self.set_status("Save the scenario before running")
                return

        path = self._editor.file_path
        if not path:
            self.set_status("Save the scenario first")
            return

        self._exec_dock.show()
        self._exec_dock.raise_()
        self._run_panel.run_command(command, path)

    # ------------------------------------------------------------------ #
    #  Menu bar                                                           #
    # ------------------------------------------------------------------ #

    def _setup_menu_bar(self) -> None:
        """Build the complete menu bar."""
        mb = self.menuBar()

        # -- File --
        file_menu = mb.addMenu("&File")

        self._act_new = QAction("&New Scenario", self)
        self._act_new.setShortcut(QKeySequence.StandardKey.New)
        self._act_new.setStatusTip("Create a new empty scenario")
        self._act_new.triggered.connect(self._on_new)
        file_menu.addAction(self._act_new)

        self._act_open = QAction("&Open...", self)
        self._act_open.setShortcut(QKeySequence.StandardKey.Open)
        self._act_open.setStatusTip("Open an existing scenario file")
        self._act_open.triggered.connect(self._on_open)
        file_menu.addAction(self._act_open)

        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._update_recent_menu()

        file_menu.addSeparator()

        self._act_save = QAction("&Save", self)
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.setEnabled(False)
        self._act_save.triggered.connect(self._on_save)
        file_menu.addAction(self._act_save)

        self._act_save_as = QAction("Save &As...", self)
        self._act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._act_save_as.setEnabled(False)
        self._act_save_as.triggered.connect(self._on_save_as)
        file_menu.addAction(self._act_save_as)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # -- Edit --
        edit_menu = mb.addMenu("&Edit")

        self._act_undo = QAction("&Undo", self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setEnabled(False)
        edit_menu.addAction(self._act_undo)

        self._act_redo = QAction("&Redo", self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setEnabled(False)
        edit_menu.addAction(self._act_redo)

        edit_menu.addSeparator()

        self._act_copy = QAction("&Copy Steps", self)
        self._act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self._act_copy.setEnabled(False)
        self._act_copy.triggered.connect(self._on_copy)
        edit_menu.addAction(self._act_copy)

        self._act_paste = QAction("&Paste Steps", self)
        self._act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self._act_paste.setEnabled(False)
        self._act_paste.triggered.connect(self._on_paste)
        edit_menu.addAction(self._act_paste)

        self._act_duplicate = QAction("&Duplicate Step", self)
        self._act_duplicate.setShortcut(QKeySequence("Ctrl+D"))
        self._act_duplicate.setEnabled(False)
        edit_menu.addAction(self._act_duplicate)

        self._act_delete = QAction("Delete Step", self)
        self._act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self._act_delete.setEnabled(False)
        edit_menu.addAction(self._act_delete)

        # -- View --
        view_menu = mb.addMenu("&View")

        self._act_toggle_sidebar = self._sidebar_dock.toggleViewAction()
        self._act_toggle_sidebar.setText("&Sidebar")
        self._act_toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        view_menu.addAction(self._act_toggle_sidebar)

        self._act_toggle_console = self._exec_dock.toggleViewAction()
        self._act_toggle_console.setText("&Console")
        self._act_toggle_console.setShortcut(QKeySequence("Ctrl+`"))
        view_menu.addAction(self._act_toggle_console)

        view_menu.addSeparator()

        theme_menu = view_menu.addMenu("&Theme")
        for theme_name in self.theme_engine.available_themes():
            act = QAction(theme_name.replace("-", " ").title(), self)
            act.setCheckable(True)
            current = self.theme_engine.current
            if current and current.source_path and current.source_path.stem == theme_name:
                act.setChecked(True)
            act.triggered.connect(lambda checked, name=theme_name: self._on_switch_theme(name))
            theme_menu.addAction(act)

        self._act_cycle_theme = QAction("Cycle Theme", self)
        self._act_cycle_theme.setShortcut(QKeySequence("Ctrl+T"))
        self._act_cycle_theme.triggered.connect(self._on_cycle_theme)
        view_menu.addAction(self._act_cycle_theme)

        # -- Tools --
        tools_menu = mb.addMenu("&Tools")

        self._act_validate = QAction("&Validate", self)
        self._act_validate.setShortcut(QKeySequence("F5"))
        self._act_validate.setStatusTip("Validate current scenario")
        self._act_validate.setEnabled(False)
        tools_menu.addAction(self._act_validate)

        self._act_preview = QAction("&Preview", self)
        self._act_preview.setShortcut(QKeySequence("F6"))
        self._act_preview.setStatusTip("Preview scenario in browser (no recording)")
        self._act_preview.setEnabled(False)
        tools_menu.addAction(self._act_preview)

        self._act_run = QAction("&Run", self)
        self._act_run.setShortcut(QKeySequence("F7"))
        self._act_run.setStatusTip("Record video without narration")
        self._act_run.setEnabled(False)
        tools_menu.addAction(self._act_run)

        self._act_full = QAction("&Full (with TTS)", self)
        self._act_full.setShortcut(QKeySequence("F8"))
        self._act_full.setStatusTip("Record video with TTS narration")
        self._act_full.setEnabled(False)
        tools_menu.addAction(self._act_full)

        tools_menu.addSeparator()

        self._act_config = QAction("&Configuration...", self)
        self._act_config.setShortcut(QKeySequence("Ctrl+,"))
        self._act_config.setStatusTip("Open configuration editor")
        tools_menu.addAction(self._act_config)

        tools_menu.addSeparator()

        self._act_record_macro = QAction("Record &Macro...", self)
        self._act_record_macro.setShortcut(QKeySequence("Ctrl+R"))
        self._act_record_macro.setStatusTip("Record browser interactions to JSON")
        tools_menu.addAction(self._act_record_macro)

        # -- Help --
        help_menu = mb.addMenu("&Help")

        self._act_shortcuts = QAction("&Keyboard Shortcuts", self)
        self._act_shortcuts.setShortcut(QKeySequence("Ctrl+/"))
        self._act_shortcuts.triggered.connect(self._on_show_shortcuts)
        help_menu.addAction(self._act_shortcuts)

        help_menu.addSeparator()

        act_about = QAction("&About NeuraScreen", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ #
    #  Toolbar                                                            #
    # ------------------------------------------------------------------ #

    def _setup_toolbar(self) -> None:
        """Build the main toolbar."""
        toolbar = QToolBar("Main")
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)

        toolbar.addAction(self._act_new)
        toolbar.addAction(self._act_open)
        toolbar.addAction(self._act_save)
        toolbar.addSeparator()
        toolbar.addAction(self._act_validate)
        toolbar.addAction(self._act_preview)
        toolbar.addAction(self._act_run)
        toolbar.addAction(self._act_full)

        self.addToolBar(toolbar)

    # ------------------------------------------------------------------ #
    #  Status bar                                                         #
    # ------------------------------------------------------------------ #

    def _setup_status_bar(self) -> None:
        """Set up the status bar with permanent widgets."""
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_msg = QLabel("Ready")
        self._status_msg.setContentsMargins(12, 0, 0, 0)
        sb.addWidget(self._status_msg, 1)

        theme = self.theme_engine.current
        theme_name = theme.name if theme else "Default"
        self._status_theme = QLabel(f"Theme: {theme_name}")
        self._status_theme.setProperty("muted", True)
        sb.addPermanentWidget(self._status_theme)

    def set_status(self, message: str) -> None:
        """Update the status bar message."""
        self._status_msg.setText(message)

    # ------------------------------------------------------------------ #
    #  Editor connections                                                  #
    # ------------------------------------------------------------------ #

    def _connect_editor(self) -> None:
        """Connect editor signals to menu actions and window updates."""
        # Undo/Redo via editor's QUndoStack
        undo_stack = self._editor.undo_stack
        self._act_undo.triggered.connect(undo_stack.undo)
        self._act_redo.triggered.connect(undo_stack.redo)
        undo_stack.canUndoChanged.connect(self._act_undo.setEnabled)
        undo_stack.canRedoChanged.connect(self._act_redo.setEnabled)

        # Dirty state
        self._editor.dirty_changed.connect(self._on_dirty_changed)
        self._editor.title_changed.connect(self._on_editor_title_changed)

    def _enable_editor_actions(self, enabled: bool = True) -> None:
        """Enable/disable actions that require an open scenario."""
        self._act_save.setEnabled(enabled)
        self._act_save_as.setEnabled(enabled)
        self._act_copy.setEnabled(enabled)
        self._act_paste.setEnabled(enabled)
        self._act_duplicate.setEnabled(enabled)
        self._act_delete.setEnabled(enabled)
        self._act_validate.setEnabled(enabled)
        self._act_preview.setEnabled(enabled)
        self._act_run.setEnabled(enabled)
        self._act_full.setEnabled(enabled)

    def _show_editor(self) -> None:
        """Switch to the editor view."""
        self._central_stack.setCurrentIndex(1)
        self._enable_editor_actions(True)

    # ------------------------------------------------------------------ #
    #  State persistence                                                  #
    # ------------------------------------------------------------------ #

    def _restore_state(self) -> None:
        geometry = self.settings.value(SETTINGS_GEOMETRY)
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1400, 900)
            screen = QApplication.primaryScreen()
            if screen:
                rect = screen.availableGeometry()
                self.move(
                    (rect.width() - self.width()) // 2,
                    (rect.height() - self.height()) // 2,
                )

        state = self.settings.value(SETTINGS_STATE)
        if state:
            self.restoreState(state)

    def _save_state(self) -> None:
        self.settings.setValue(SETTINGS_GEOMETRY, self.saveGeometry())
        self.settings.setValue(SETTINGS_STATE, self.saveState())
        self.settings.sync()

    def closeEvent(self, event) -> None:
        if self._editor.is_dirty:
            result = QMessageBox.question(
                self, "Unsaved Changes",
                "There are unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Save:
                if not self._editor.save():
                    event.ignore()
                    return
            elif result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        self._save_state()
        self._save_recent_files()
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  Recent files                                                       #
    # ------------------------------------------------------------------ #

    def _load_recent_files(self) -> None:
        files = self.settings.value(SETTINGS_RECENT_FILES, [])
        if isinstance(files, list):
            self._recent_files = [f for f in files if Path(f).exists()]
        self._update_recent_menu()

    def _save_recent_files(self) -> None:
        self.settings.setValue(SETTINGS_RECENT_FILES, self._recent_files[:MAX_RECENT_FILES])

    def add_recent_file(self, path: str) -> None:
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:MAX_RECENT_FILES]
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        self._recent_menu.clear()
        if not self._recent_files:
            act = QAction("(no recent files)", self)
            act.setEnabled(False)
            self._recent_menu.addAction(act)
            return
        for filepath in self._recent_files:
            name = Path(filepath).name
            act = QAction(name, self)
            act.setStatusTip(filepath)
            act.triggered.connect(lambda checked, p=filepath: self._open_file(p))
            self._recent_menu.addAction(act)

    # ------------------------------------------------------------------ #
    #  Slots                                                              #
    # ------------------------------------------------------------------ #

    def _on_new(self) -> None:
        """Create a new scenario."""
        self._editor.new_scenario()
        self._show_editor()
        self.set_status("New scenario")

    def _on_open(self) -> None:
        """Open a scenario file via dialog."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Scenario", "",
            "JSON Scenarios (*.json);;All Files (*)",
        )
        if filepath:
            self._open_file(filepath)

    def _open_file(self, filepath: str) -> None:
        """Open a specific scenario file."""
        if self._editor.open_file(filepath):
            self.add_recent_file(filepath)
            self._show_editor()
            self.set_status(f"Opened: {Path(filepath).name}")

    def _on_save(self) -> None:
        """Save current scenario."""
        if self._editor.save():
            self.set_status("Saved")

    def _on_save_as(self) -> None:
        """Save current scenario as new file."""
        if self._editor.save_as():
            path = self._editor.file_path
            if path:
                self.add_recent_file(path)
            self.set_status(f"Saved as: {Path(path).name}" if path else "Saved")

    def _on_copy(self) -> None:
        self._editor.copy_steps()

    def _on_paste(self) -> None:
        self._editor.paste_steps()

    def _on_dirty_changed(self, dirty: bool) -> None:
        """Update window title with dirty indicator."""
        title = self._editor._metadata.get("title", APP_NAME)
        path = self._editor.file_path
        if path:
            title = f"{Path(path).name} — {title}"
        if dirty:
            title = f"* {title}"
        self.setWindowTitle(f"{title} — {APP_NAME}")

    def _on_editor_title_changed(self, title: str) -> None:
        """Update window title when scenario title changes."""
        self._on_dirty_changed(self._editor.is_dirty)

    def _on_switch_theme(self, name: str) -> None:
        theme = self.theme_engine.apply_theme(name)
        self._status_theme.setText(f"Theme: {theme.name}")
        self.settings.setValue(SETTINGS_THEME, name)
        self._update_theme_menu_checks(name)
        self.set_status(f"Theme: {theme.name}")

    def _on_cycle_theme(self) -> None:
        theme = self.theme_engine.cycle_theme()
        name = theme.source_path.stem if theme.source_path else ""
        self._status_theme.setText(f"Theme: {theme.name}")
        self.settings.setValue(SETTINGS_THEME, name)
        self._update_theme_menu_checks(name)
        self.set_status(f"Theme: {theme.name}")

    def _update_theme_menu_checks(self, active_name: str) -> None:
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu and action.text().replace("&", "") == "View":
                for sub_action in menu.actions():
                    sub_menu = sub_action.menu()
                    if sub_menu and sub_action.text().replace("&", "") == "Theme":
                        for theme_act in sub_menu.actions():
                            theme_id = theme_act.text().lower().replace(" ", "-")
                            theme_act.setChecked(theme_id == active_name)
                        break
                break

    def _on_show_shortcuts(self) -> None:
        shortcuts = [
            ("Ctrl+N", "New scenario"),
            ("Ctrl+O", "Open scenario"),
            ("Ctrl+S", "Save"),
            ("Ctrl+Shift+S", "Save as"),
            ("Ctrl+Z", "Undo"),
            ("Ctrl+Shift+Z", "Redo"),
            ("Ctrl+C", "Copy steps"),
            ("Ctrl+V", "Paste steps"),
            ("Ctrl+D", "Duplicate step"),
            ("Del", "Delete step"),
            ("F5", "Validate"),
            ("F6", "Preview"),
            ("F7", "Run"),
            ("F8", "Full (with TTS)"),
            ("Ctrl+R", "Record macro"),
            ("Ctrl+,", "Configuration"),
            ("Ctrl+B", "Toggle sidebar"),
            ("Ctrl+T", "Cycle theme"),
            ("Ctrl+/", "Keyboard shortcuts"),
            ("Ctrl+Q", "Quit"),
        ]
        text = "\n".join(f"  {key:<20} {desc}" for key, desc in shortcuts)
        QMessageBox.information(
            self, "Keyboard Shortcuts",
            f"NeuraScreen Shortcuts\n\n{text}",
        )

    def _on_about(self) -> None:
        version = self._get_version()
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {version}</p>"
            f"<p>Automated demo video generator for web applications.</p>"
            f"<p>Write a JSON scenario, generate a narrated video.</p>"
            f"<hr>"
            f"<p>License: MIT</p>"
            f"<p><a href='https://github.com/NEURASCOPE/neurascreen'>GitHub</a></p>",
        )

    @staticmethod
    def _get_version() -> str:
        try:
            from neurascreen import __version__
            return __version__
        except ImportError:
            return "dev"
