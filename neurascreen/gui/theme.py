"""Theme engine: load JSON palettes and generate QSS stylesheets."""

import json
import logging
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

logger = logging.getLogger("neurascreen.gui")

# Built-in themes directory
THEMES_DIR = Path(__file__).parent / "themes"

# Resources directory (SVG icons)
RESOURCES_DIR = Path(__file__).parent / "resources"

# User themes directory
USER_THEMES_DIR = Path.home() / ".neurascreen" / "themes"

# Default theme
DEFAULT_THEME = "dark-teal"

# Required color keys (validation)
REQUIRED_COLORS = {
    "primary", "primary_light", "primary_dark", "accent",
    "background", "surface", "surface_alt", "border",
    "text", "text_secondary", "text_muted",
    "success", "warning", "error", "info",
    "selection", "selection_text", "hover", "pressed",
}


class Theme:
    """Represents a loaded theme with its palette and properties."""

    def __init__(self, data: dict, source_path: Path | None = None):
        self.name: str = data.get("name", "Untitled")
        self.variant: str = data.get("variant", "dark")
        self.colors: dict[str, str] = data.get("colors", {})
        self.fonts: dict[str, str | int] = data.get("fonts", {})
        self.radius: int = data.get("radius", 6)
        self.radius_sm: int = data.get("radius_sm", 4)
        self.radius_lg: int = data.get("radius_lg", 8)
        self.spacing: int = data.get("spacing", 8)
        self.border_width: int = data.get("border_width", 1)
        self.source_path = source_path

    @property
    def is_dark(self) -> bool:
        return self.variant == "dark"

    def color(self, key: str, fallback: str = "#FF00FF") -> str:
        """Get a color value by key with fallback."""
        return self.colors.get(key, fallback)

    def font_family(self) -> str:
        return str(self.fonts.get("family", "sans-serif"))

    def font_monospace(self) -> str:
        return str(self.fonts.get("monospace", "monospace"))

    def font_size(self, size: str = "md") -> int:
        key = f"size_{size}"
        return int(self.fonts.get(key, 13))


class ThemeEngine:
    """Discovers, loads, and applies themes."""

    def __init__(self):
        self._themes: dict[str, Path] = {}
        self._current: Theme | None = None
        self._discover_themes()

    def _discover_themes(self) -> None:
        """Scan built-in and user theme directories."""
        self._themes.clear()

        # Built-in themes
        if THEMES_DIR.exists():
            for f in THEMES_DIR.glob("*.json"):
                self._themes[f.stem] = f

        # User themes (override built-in if same name)
        if USER_THEMES_DIR.exists():
            for f in USER_THEMES_DIR.glob("*.json"):
                self._themes[f.stem] = f

    def available_themes(self) -> list[str]:
        """Return sorted list of available theme names."""
        return sorted(self._themes.keys())

    def load_theme(self, name: str) -> Theme:
        """Load a theme by name."""
        if name not in self._themes:
            logger.warning(f"Theme '{name}' not found, falling back to '{DEFAULT_THEME}'")
            name = DEFAULT_THEME

        path = self._themes[name]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to load theme '{name}' from {path}: {e}") from e

        # Validate required colors
        missing = REQUIRED_COLORS - set(data.get("colors", {}).keys())
        if missing:
            logger.warning(f"Theme '{name}' missing colors: {missing}")

        theme = Theme(data, source_path=path)
        logger.info(f"Loaded theme: {theme.name} ({theme.variant})")
        return theme

    def apply_theme(self, name: str, app: QApplication | None = None) -> Theme:
        """Load and apply a theme to the application."""
        theme = self.load_theme(name)
        self._current = theme

        qss = generate_qss(theme)
        target = app or QApplication.instance()
        if target:
            target.setStyleSheet(qss)
            _apply_palette(theme, target)
            logger.info(f"Applied theme: {theme.name}")
        else:
            logger.warning("No QApplication instance to apply theme to")

        return theme

    @property
    def current(self) -> Theme | None:
        return self._current

    def cycle_theme(self, app: QApplication | None = None) -> Theme:
        """Switch to the next available theme."""
        themes = self.available_themes()
        if not themes:
            raise RuntimeError("No themes available")

        current_name = ""
        if self._current and self._current.source_path:
            current_name = self._current.source_path.stem

        try:
            idx = themes.index(current_name)
            next_name = themes[(idx + 1) % len(themes)]
        except ValueError:
            next_name = themes[0]

        return self.apply_theme(next_name, app)

    def reload(self) -> None:
        """Re-discover themes (useful after user adds a new theme file)."""
        self._discover_themes()


def _apply_palette(theme: Theme, app: QApplication) -> None:
    """Set the QPalette to match the theme so Fusion respects our colors.

    Note: Fusion uses HighlightedText for pressed button text, so we must
    keep it dark in light themes to avoid white-on-light flash.
    The QSS ::item:selected rules handle list/tree selection text separately.
    """
    c = theme.colors
    text_color = QColor(c.get("text", "#0F172A"))
    palette = QPalette()

    bg_color = QColor(c.get("background", "#F8FAFC"))
    surface_color = QColor(c.get("surface", "#FFFFFF"))
    surface_alt = QColor(c.get("surface_alt", "#F1F5F9"))
    border_color = QColor(c.get("border", "#CBD5E1"))
    selection_color = QColor(c.get("selection", "#0D9488"))
    hover_color = QColor(c.get("hover", "#E2E8F0"))
    muted_color = QColor(c.get("text_muted", "#94A3B8"))

    tooltip_bg = QColor(c.get("tooltip_bg", "#333"))
    tooltip_text = QColor(c.get("tooltip_text", "#FFF"))
    disabled_text = QColor(c.get("disabled_text", "#CBD5E1"))
    disabled_bg = QColor(c.get("disabled_bg", "#F1F5F9"))

    palette = QPalette()

    # Set colors for ALL three color groups so Fusion never falls back
    # to system defaults (which cause white text on pressed buttons).
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
    ):
        # Text roles — all dark in light theme, all light in dark theme
        for role in (
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText,
            QPalette.ColorRole.HighlightedText,
            QPalette.ColorRole.BrightText,
        ):
            palette.setColor(group, role, text_color)

        # Background roles
        palette.setColor(group, QPalette.ColorRole.Window, bg_color)
        palette.setColor(group, QPalette.ColorRole.Base, surface_color)
        palette.setColor(group, QPalette.ColorRole.AlternateBase, surface_alt)
        palette.setColor(group, QPalette.ColorRole.Button, surface_alt)
        palette.setColor(group, QPalette.ColorRole.Highlight, selection_color)
        palette.setColor(group, QPalette.ColorRole.Light, hover_color)
        palette.setColor(group, QPalette.ColorRole.Midlight, hover_color)
        palette.setColor(group, QPalette.ColorRole.Mid, border_color)
        palette.setColor(group, QPalette.ColorRole.Dark, border_color)
        palette.setColor(group, QPalette.ColorRole.Shadow, border_color)
        palette.setColor(group, QPalette.ColorRole.PlaceholderText, muted_color)
        palette.setColor(group, QPalette.ColorRole.ToolTipBase, tooltip_bg)
        palette.setColor(group, QPalette.ColorRole.ToolTipText, tooltip_text)

    # Disabled group
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.HighlightedText,
        QPalette.ColorRole.BrightText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled_text)

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, bg_color)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, disabled_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, disabled_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, border_color)

    app.setPalette(palette)


def generate_qss(theme: Theme) -> str:
    """Generate a complete QSS stylesheet from a theme."""
    c = theme.colors
    f = theme.fonts
    r = theme.radius
    r_sm = theme.radius_sm
    r_lg = theme.radius_lg
    bw = theme.border_width
    sp = theme.spacing

    font_family = theme.font_family()
    font_mono = theme.font_monospace()
    font_sm = theme.font_size("sm")
    font_md = theme.font_size("md")
    font_lg = theme.font_size("lg")

    # Helper for color access with defaults
    def col(key: str, fallback: str = "#888") -> str:
        return c.get(key, fallback)

    # SVG arrow paths (forward slashes for QSS url())
    arrow_up = str(RESOURCES_DIR / "arrow-up.svg").replace("\\", "/")
    arrow_down = str(RESOURCES_DIR / "arrow-down.svg").replace("\\", "/")

    return f"""
/* ================================================================
   NeuraScreen Theme: {theme.name}
   Generated from JSON palette — do not edit manually
   ================================================================ */

/* --- Global --- */
* {{
    font-family: {font_family};
    font-size: {font_md}px;
    color: {col('text')};
    outline: none;
}}

/* --- Main Window --- */
QMainWindow {{
    background-color: {col('background')};
}}

QMainWindow::separator {{
    background-color: {col('background')};
    width: 10px;
    height: 10px;
}}

/* --- Menu Bar --- */
QMenuBar {{
    background-color: {col('menubar_bg', col('background'))};
    color: {col('text')};
    border-bottom: {bw}px solid {col('border')};
    padding: 2px 0;
    font-size: {font_md}px;
}}

QMenuBar::item {{
    padding: 4px 10px;
    border-radius: {r_sm}px;
    margin: 1px 2px;
}}

QMenuBar::item:selected {{
    background-color: {col('hover')};
}}

QMenuBar::item:pressed {{
    background-color: {col('pressed')};
    color: {col('pressed_text', col('text'))};
}}

/* --- Menus --- */
QMenu {{
    background-color: {col('menu_bg', col('surface'))};
    border: {bw}px solid {col('border')};
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 28px 6px 12px;
    border-radius: {r_sm}px;
    margin: 1px 4px;
}}

QMenu::item:selected {{
    background-color: {col('menu_hover', col('hover'))};
    color: {col('text')};
}}

QMenu::item:disabled {{
    color: {col('disabled_text')};
}}

QMenu::separator {{
    height: 1px;
    background-color: {col('border')};
    margin: 4px 8px;
}}

QMenu::icon {{
    padding-left: 8px;
}}

/* --- Toolbar --- */
QToolBar {{
    background-color: {col('toolbar_bg', col('surface'))};
    border-bottom: {bw}px solid {col('toolbar_border', col('border'))};
    padding: 4px {sp}px;
    spacing: {sp}px;
}}

QToolBar::separator {{
    width: 1px;
    background-color: {col('border')};
    margin: 4px 6px;
}}

QToolButton {{
    background-color: transparent;
    border: {bw}px solid transparent;
    border-radius: {r}px;
    padding: 6px 12px;
    color: {col('text')};
    font-size: {font_md}px;
}}

QToolButton:hover {{
    background-color: {col('hover')};
    border-color: {col('border')};
}}

QToolButton:pressed {{
    background-color: {col('pressed')};
    color: {col('pressed_text', col('text'))};
}}

QToolButton:checked {{
    background-color: {col('primary')};
    color: {col('selection_text')};
    border-color: {col('primary_dark')};
}}

QToolButton:disabled {{
    color: {col('disabled_text')};
}}

/* --- Push Buttons --- */
QPushButton {{
    background-color: {col('surface_alt')};
    color: {col('text')};
    border: {bw}px solid {col('border')};
    border-radius: {r}px;
    padding: 6px 16px;
    font-size: {font_md}px;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {col('hover')};
    border-color: {col('primary_light')};
}}

QPushButton:pressed {{
    background-color: {col('pressed')};
    color: {col('pressed_text', col('text'))};
    border-color: {col('primary_dark')};
}}

QPushButton:disabled {{
    background-color: {col('disabled_bg')};
    color: {col('disabled_text')};
    border-color: {col('border')};
}}

QPushButton[primary="true"] {{
    background-color: {col('primary')};
    color: {col('selection_text')};
    border-color: {col('primary_dark')};
    font-weight: bold;
}}

QPushButton[primary="true"]:hover {{
    background-color: {col('primary_light')};
}}

QPushButton[primary="true"]:pressed {{
    background-color: {col('primary_dark')};
}}

QPushButton[danger="true"] {{
    background-color: {col('error')};
    color: #FFFFFF;
    border-color: {col('error')};
}}

/* --- Line Edit --- */
QLineEdit {{
    background-color: {col('input_bg', col('surface'))};
    color: {col('text')};
    border: {bw}px solid {col('input_border', col('border'))};
    border-radius: {r}px;
    padding: 6px 10px;
    font-size: {font_md}px;
    selection-background-color: {col('selection')};
    selection-color: {col('selection_text')};
}}

QLineEdit:focus {{
    border-color: {col('input_focus_border', col('primary'))};
}}

QLineEdit:disabled {{
    background-color: {col('disabled_bg')};
    color: {col('disabled_text')};
}}

QLineEdit[readOnly="true"] {{
    background-color: {col('surface_alt')};
}}

/* --- Text Edit / Plain Text Edit --- */
QTextEdit, QPlainTextEdit {{
    background-color: {col('input_bg', col('surface'))};
    color: {col('text')};
    border: {bw}px solid {col('input_border', col('border'))};
    padding: 6px;
    font-size: {font_md}px;
    selection-background-color: {col('selection')};
    selection-color: {col('selection_text')};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {col('input_focus_border', col('primary'))};
}}

QPlainTextEdit[monospace="true"] {{
    font-family: {font_mono};
    font-size: {font_sm}px;
}}

/* --- Spin Box --- */
QSpinBox, QDoubleSpinBox {{
    background-color: {col('input_bg', col('surface'))};
    color: {col('text')};
    border: {bw}px solid {col('input_border', col('border'))};
    border-radius: {r}px;
    padding: 4px 8px;
    font-size: {font_md}px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {col('input_focus_border', col('primary'))};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    background-color: {col('surface_alt')};
    border-left: {bw}px solid {col('border')};
    border-top-right-radius: {r}px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    background-color: {col('surface_alt')};
    border-left: {bw}px solid {col('border')};
    border-bottom-right-radius: {r}px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {col('hover')};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({arrow_up});
    width: 10px;
    height: 10px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({arrow_down});
    width: 10px;
    height: 10px;
}}

/* --- Combo Box --- */
QComboBox {{
    background-color: {col('input_bg', col('surface'))};
    color: {col('text')};
    border: {bw}px solid {col('input_border', col('border'))};
    border-radius: {r}px;
    padding: 5px 10px;
    font-size: {font_md}px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {col('primary_light')};
}}

QComboBox:focus {{
    border-color: {col('input_focus_border', col('primary'))};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
    background-color: transparent;
}}

QComboBox QAbstractItemView {{
    background-color: {col('menu_bg', col('surface'))};
    color: {col('text')};
    border: {bw}px solid {col('border')};
    selection-background-color: {col('selection')};
    selection-color: {col('selection_text')};
    padding: 4px;
}}

/* --- Check Box --- */
QCheckBox {{
    spacing: {sp}px;
    padding-right: 4px;
    color: {col('text')};
    font-size: {font_md}px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: {bw}px solid {col('border')};
    border-radius: {r_sm}px;
    background-color: {col('input_bg', col('surface'))};
}}

QCheckBox::indicator:checked {{
    background-color: {col('primary')};
    border-color: {col('primary_dark')};
}}

QCheckBox::indicator:hover {{
    border-color: {col('primary_light')};
}}

QCheckBox::indicator:disabled {{
    background-color: {col('disabled_bg')};
    border-color: {col('disabled_text')};
}}

/* --- Radio Button --- */
QRadioButton {{
    spacing: {sp}px;
    color: {col('text')};
    font-size: {font_md}px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: {bw}px solid {col('border')};
    border-radius: 9px;
    background-color: {col('input_bg', col('surface'))};
}}

QRadioButton::indicator:checked {{
    background-color: {col('primary')};
    border-color: {col('primary_dark')};
}}

/* --- Group Box --- */
QGroupBox {{
    background-color: {col('surface')};
    border: {bw}px solid {col('border')};
    margin-top: 14px;
    padding: {sp + 8}px {sp}px {sp}px {sp}px;
    font-size: {font_md}px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {col('primary_light')};
}}

/* --- Tab Widget --- */
QTabWidget::pane {{
    background-color: {col('surface')};
    border: none;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {col('tab_inactive', col('surface_alt'))};
    color: {col('text_secondary')};
    border: {bw}px solid {col('border')};
    border-bottom: none;
    border-top-left-radius: {r}px;
    border-top-right-radius: {r}px;
    padding: 6px 16px;
    margin-right: 2px;
    font-size: {font_md}px;
}}

QTabBar::tab:selected {{
    background-color: {col('surface')};
    color: {col('text')};
    border-bottom: 2px solid {col('tab_active', col('primary'))};
}}

QTabBar::tab:hover:!selected {{
    background-color: {col('hover')};
    color: {col('text')};
}}

/* --- List View / Tree View / Table View --- */
QListView, QTreeView, QTableView {{
    background-color: {col('surface')};
    color: {col('text')};
    border: {bw}px solid {col('border')};
    alternate-background-color: {col('surface_alt')};
    font-size: {font_md}px;
}}

QListView::item, QTreeView::item, QTableView::item {{
    padding: 4px 8px;
    border-radius: {r_sm}px;
}}

QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
    background-color: {col('selection')};
    color: {col('selection_text')};
}}

QListView::item:hover, QTreeView::item:hover, QTableView::item:hover {{
    background-color: {col('hover')};
    color: {col('text')};
}}

QListView::item:selected:hover, QTreeView::item:selected:hover, QTableView::item:selected:hover {{
    background-color: {col('selection')};
    color: {col('selection_text')};
}}

QListView::item:pressed, QTreeView::item:pressed, QTableView::item:pressed {{
    background-color: {col('selection')};
    color: {col('selection_text')};
}}

QHeaderView::section {{
    background-color: {col('surface_alt')};
    color: {col('text_secondary')};
    border: none;
    border-right: 1px solid {col('border')};
    border-bottom: {bw}px solid {col('border')};
    padding: 6px 8px;
    font-size: {font_sm}px;
    font-weight: bold;
}}

/* --- Scroll Bar --- */
QScrollBar:vertical {{
    background-color: {col('scrollbar_bg', col('surface'))};
    width: 10px;
    margin: 0;
    border: none;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {col('scrollbar_handle', col('border'))};
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {col('scrollbar_handle_hover', col('text_muted'))};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {col('scrollbar_bg', col('surface'))};
    height: 10px;
    margin: 0;
    border: none;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {col('scrollbar_handle', col('border'))};
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {col('scrollbar_handle_hover', col('text_muted'))};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* --- Scroll Area --- */
QScrollArea {{
    background-color: {col('surface')};
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: {col('surface')};
}}

/* --- Stacked Widget --- */
QStackedWidget {{
    background-color: {col('background')};
}}

/* --- Splitter --- */
QSplitter::handle {{
    background-color: transparent;
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* --- Status Bar --- */
QStatusBar {{
    background-color: {col('statusbar_bg', col('background'))};
    color: {col('text_secondary')};
    border-top: {bw}px solid {col('border')};
    font-size: {font_sm}px;
    padding: 4px 16px;
}}

QStatusBar::item {{
    border: none;
}}

/* --- Dock Widget --- */
QDockWidget {{
    color: {col('text')};
    font-size: {font_md}px;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {col('dock_title_bg', col('surface'))};
    border: {bw}px solid {col('border')};
    padding: 6px 10px;
    text-align: left;
    font-weight: bold;
    font-size: {font_sm}px;
}}

/* --- Dialog --- */
QDialog {{
    background-color: {col('background')};
}}

/* --- Tooltip --- */
QToolTip {{
    background-color: {col('tooltip_bg', col('surface_alt'))};
    color: {col('tooltip_text', col('text'))};
    border: {bw}px solid {col('tooltip_border', col('border'))};
    border-radius: {r_sm}px;
    padding: 4px 8px;
    font-size: {font_sm}px;
}}

/* --- Progress Bar --- */
QProgressBar {{
    background-color: {col('surface_alt')};
    border: {bw}px solid {col('border')};
    border-radius: {r}px;
    text-align: center;
    color: {col('text')};
    font-size: {font_sm}px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {col('primary')};
    border-radius: {r}px;
}}

/* --- Label --- */
QLabel {{
    color: {col('text')};
    font-size: {font_md}px;
    background-color: transparent;
}}

QLabel[heading="true"] {{
    font-size: {font_lg}px;
    font-weight: bold;
    color: {col('text')};
}}

QLabel[subheading="true"] {{
    font-size: {font_md}px;
    color: {col('text_secondary')};
}}

QLabel[muted="true"] {{
    color: {col('text_muted')};
    font-size: {font_sm}px;
}}

QLabel[error_label="true"] {{
    color: {col('error')};
}}

QLabel[success_label="true"] {{
    color: {col('success')};
}}

/* --- Frame --- */
QFrame[frameShape="4"] {{
    color: {col('border')};
    max-height: 1px;
}}

QFrame[frameShape="5"] {{
    color: {col('border')};
    max-width: 1px;
}}
"""
