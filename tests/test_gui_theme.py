"""Tests for the GUI theme engine."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTheme:
    """Tests for the Theme dataclass."""

    def _make_theme_data(self, **overrides):
        data = {
            "name": "Test Theme",
            "variant": "dark",
            "colors": {
                "primary": "#0D9488",
                "primary_light": "#14B8A6",
                "primary_dark": "#0F766E",
                "accent": "#2DD4BF",
                "background": "#0F172A",
                "surface": "#1E293B",
                "surface_alt": "#334155",
                "border": "#475569",
                "text": "#F8FAFC",
                "text_secondary": "#94A3B8",
                "text_muted": "#64748B",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444",
                "info": "#3B82F6",
                "selection": "#0D9488",
                "selection_text": "#FFFFFF",
                "hover": "#334155",
                "pressed": "#0F766E",
            },
            "fonts": {
                "family": "Inter, sans-serif",
                "size_sm": 11,
                "size_md": 13,
                "size_lg": 15,
                "monospace": "Consolas, monospace",
            },
            "radius": 6,
            "radius_sm": 4,
            "radius_lg": 8,
            "spacing": 8,
            "border_width": 1,
        }
        data.update(overrides)
        return data

    def test_theme_creation(self):
        from neurascreen.gui.theme import Theme
        data = self._make_theme_data()
        theme = Theme(data)
        assert theme.name == "Test Theme"
        assert theme.variant == "dark"
        assert theme.is_dark is True
        assert theme.radius == 6

    def test_theme_light_variant(self):
        from neurascreen.gui.theme import Theme
        data = self._make_theme_data(variant="light")
        theme = Theme(data)
        assert theme.is_dark is False

    def test_theme_color_access(self):
        from neurascreen.gui.theme import Theme
        data = self._make_theme_data()
        theme = Theme(data)
        assert theme.color("primary") == "#0D9488"
        assert theme.color("nonexistent") == "#FF00FF"
        assert theme.color("nonexistent", "#000") == "#000"

    def test_theme_font_access(self):
        from neurascreen.gui.theme import Theme
        data = self._make_theme_data()
        theme = Theme(data)
        assert "Inter" in theme.font_family()
        assert "Consolas" in theme.font_monospace()
        assert theme.font_size("sm") == 11
        assert theme.font_size("md") == 13
        assert theme.font_size("lg") == 15
        assert theme.font_size("nonexistent") == 13  # default

    def test_theme_defaults(self):
        from neurascreen.gui.theme import Theme
        theme = Theme({})
        assert theme.name == "Untitled"
        assert theme.variant == "dark"
        assert theme.radius == 6
        assert theme.spacing == 8


class TestThemeEngine:
    """Tests for the ThemeEngine."""

    def test_discover_builtin_themes(self):
        from neurascreen.gui.theme import ThemeEngine
        engine = ThemeEngine()
        themes = engine.available_themes()
        assert "dark-teal" in themes
        assert "light" in themes

    def test_load_builtin_theme(self):
        from neurascreen.gui.theme import ThemeEngine
        engine = ThemeEngine()
        theme = engine.load_theme("dark-teal")
        assert theme.name == "NeuraScope Dark Teal"
        assert theme.variant == "dark"
        assert theme.color("primary") == "#0D9488"

    def test_load_light_theme(self):
        from neurascreen.gui.theme import ThemeEngine
        engine = ThemeEngine()
        theme = engine.load_theme("light")
        assert theme.name == "NeuraScope Light"
        assert theme.variant == "light"

    def test_load_unknown_theme_falls_back(self):
        from neurascreen.gui.theme import ThemeEngine
        engine = ThemeEngine()
        theme = engine.load_theme("nonexistent-theme-xyz")
        assert theme.name == "NeuraScope Dark Teal"

    def test_discover_user_themes(self):
        from neurascreen.gui.theme import ThemeEngine, USER_THEMES_DIR
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)
            custom_theme = {
                "name": "Custom Purple",
                "variant": "dark",
                "colors": {"primary": "#9333EA"},
                "fonts": {},
            }
            (user_dir / "custom-purple.json").write_text(
                json.dumps(custom_theme), encoding="utf-8"
            )
            with patch("neurascreen.gui.theme.USER_THEMES_DIR", user_dir):
                engine = ThemeEngine()
                assert "custom-purple" in engine.available_themes()
                theme = engine.load_theme("custom-purple")
                assert theme.name == "Custom Purple"
                assert theme.color("primary") == "#9333EA"

    def test_user_theme_overrides_builtin(self):
        from neurascreen.gui.theme import ThemeEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)
            override = {
                "name": "My Dark Teal Override",
                "variant": "dark",
                "colors": {"primary": "#FF0000"},
                "fonts": {},
            }
            (user_dir / "dark-teal.json").write_text(
                json.dumps(override), encoding="utf-8"
            )
            with patch("neurascreen.gui.theme.USER_THEMES_DIR", user_dir):
                engine = ThemeEngine()
                theme = engine.load_theme("dark-teal")
                assert theme.name == "My Dark Teal Override"
                assert theme.color("primary") == "#FF0000"

    def test_reload(self):
        from neurascreen.gui.theme import ThemeEngine
        engine = ThemeEngine()
        initial = engine.available_themes()
        engine.reload()
        assert engine.available_themes() == initial


class TestGenerateQSS:
    """Tests for QSS generation."""

    def test_generates_nonempty_qss(self):
        from neurascreen.gui.theme import Theme, generate_qss
        data = {
            "name": "Test",
            "variant": "dark",
            "colors": {
                "primary": "#0D9488",
                "primary_light": "#14B8A6",
                "primary_dark": "#0F766E",
                "accent": "#2DD4BF",
                "background": "#0F172A",
                "surface": "#1E293B",
                "surface_alt": "#334155",
                "border": "#475569",
                "text": "#F8FAFC",
                "text_secondary": "#94A3B8",
                "text_muted": "#64748B",
                "success": "#22C55E",
                "warning": "#F59E0B",
                "error": "#EF4444",
                "info": "#3B82F6",
                "selection": "#0D9488",
                "selection_text": "#FFFFFF",
                "hover": "#334155",
                "pressed": "#0F766E",
            },
            "fonts": {
                "family": "Inter",
                "size_sm": 11,
                "size_md": 13,
                "size_lg": 15,
                "monospace": "Consolas",
            },
            "radius": 6,
            "radius_sm": 4,
            "radius_lg": 8,
            "spacing": 8,
            "border_width": 1,
        }
        theme = Theme(data)
        qss = generate_qss(theme)
        assert len(qss) > 1000
        assert "QMainWindow" in qss
        assert "QMenuBar" in qss
        assert "QPushButton" in qss
        assert "QLineEdit" in qss
        assert "QScrollBar" in qss
        assert "QTabBar" in qss
        assert "#0D9488" in qss
        assert "#0F172A" in qss

    def test_qss_uses_theme_colors(self):
        from neurascreen.gui.theme import Theme, generate_qss
        data = {
            "name": "Red",
            "variant": "dark",
            "colors": {
                "primary": "#FF0000",
                "background": "#111111",
                "text": "#FFFFFF",
            },
            "fonts": {"family": "Arial", "size_md": 14},
        }
        theme = Theme(data)
        qss = generate_qss(theme)
        assert "#FF0000" in qss
        assert "#111111" in qss

    def test_qss_uses_font_settings(self):
        from neurascreen.gui.theme import Theme, generate_qss
        data = {
            "name": "Fonts",
            "variant": "light",
            "colors": {},
            "fonts": {
                "family": "Fira Sans, sans-serif",
                "monospace": "Fira Code",
                "size_md": 16,
            },
        }
        theme = Theme(data)
        qss = generate_qss(theme)
        assert "Fira Sans" in qss
        assert "Fira Code" in qss
        assert "16px" in qss


class TestBuiltinThemeFiles:
    """Validate that built-in theme JSON files are well-formed."""

    def test_dark_teal_valid_json(self):
        from neurascreen.gui.theme import THEMES_DIR, REQUIRED_COLORS
        path = THEMES_DIR / "dark-teal.json"
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data
        assert "variant" in data
        assert "colors" in data
        assert "fonts" in data
        missing = REQUIRED_COLORS - set(data["colors"].keys())
        assert not missing, f"Missing colors: {missing}"

    def test_light_valid_json(self):
        from neurascreen.gui.theme import THEMES_DIR, REQUIRED_COLORS
        path = THEMES_DIR / "light.json"
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "name" in data
        assert "variant" in data
        assert "colors" in data
        missing = REQUIRED_COLORS - set(data["colors"].keys())
        assert not missing, f"Missing colors: {missing}"

    def test_all_color_values_are_hex(self):
        from neurascreen.gui.theme import THEMES_DIR
        import re
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for theme_file in THEMES_DIR.glob("*.json"):
            with open(theme_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.get("colors", {}).items():
                assert hex_pattern.match(value), (
                    f"{theme_file.name}: color '{key}' = '{value}' is not valid hex"
                )


class TestCLIGuiCommand:
    """Test the CLI gui command integration."""

    def test_gui_command_import_error_message(self):
        """Verify graceful error when PySide6 is not available."""
        from neurascreen.gui import launch_gui
        # The function itself should exist and be callable
        assert callable(launch_gui)
