"""QApplication wrapper: initializes theme, creates main window, runs event loop."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .theme import ThemeEngine, DEFAULT_THEME
from .main_window import MainWindow, ORG_NAME, APP_NAME, SETTINGS_THEME

logger = logging.getLogger("neurascreen.gui")


class NeuraScreenApp:
    """Application entry point: sets up QApplication, theme, and main window."""

    def __init__(self, args: list[str]):
        self._args = args
        self._app: QApplication | None = None
        self._window: MainWindow | None = None
        self._theme_engine: ThemeEngine | None = None

    def run(self) -> int:
        """Launch the application and enter the event loop."""
        self._app = QApplication(self._args)
        self._app.setApplicationName(APP_NAME)
        self._app.setOrganizationName(ORG_NAME)

        # Set up logging for GUI
        gui_logger = logging.getLogger("neurascreen.gui")
        if not gui_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            ))
            gui_logger.addHandler(handler)
            gui_logger.setLevel(logging.DEBUG)

        # Initialize theme engine and apply saved or default theme
        self._theme_engine = ThemeEngine()

        settings = QSettings(ORG_NAME, APP_NAME)
        saved_theme = settings.value(SETTINGS_THEME, DEFAULT_THEME)
        if saved_theme not in self._theme_engine.available_themes():
            saved_theme = DEFAULT_THEME
        self._theme_engine.apply_theme(saved_theme, self._app)

        # Create and show main window
        self._window = MainWindow(self._theme_engine)
        self._window.show()

        logger.info("NeuraScreen GUI started")
        return self._app.exec()
