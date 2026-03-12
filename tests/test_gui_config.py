"""Tests for the configuration manager — pure logic, no Qt dependency."""

import tempfile
from pathlib import Path


class TestFieldDefinitions:
    """Verify field definitions are complete and consistent."""

    def test_all_fields_have_required_attributes(self):
        from neurascreen.gui.config.config_fields import FIELDS
        for f in FIELDS:
            assert f.env_key, f"Field missing env_key: {f}"
            assert f.label, f"Field missing label: {f.env_key}"
            assert f.field_type, f"Field missing field_type: {f.env_key}"
            assert f.tab, f"Field missing tab: {f.env_key}"
            # default can be empty string

    def test_field_count(self):
        from neurascreen.gui.config.config_fields import FIELDS
        assert len(FIELDS) == 28

    def test_all_tabs_have_fields(self):
        from neurascreen.gui.config.config_fields import get_fields_by_tab, TABS_ORDER
        by_tab = get_fields_by_tab()
        for tab in TABS_ORDER:
            assert tab in by_tab, f"Tab {tab} missing"
            assert len(by_tab[tab]) > 0, f"Tab {tab} has no fields"

    def test_tabs_order_count(self):
        from neurascreen.gui.config.config_fields import TABS_ORDER
        assert len(TABS_ORDER) == 7

    def test_unique_env_keys(self):
        from neurascreen.gui.config.config_fields import FIELDS
        keys = [f.env_key for f in FIELDS]
        assert len(keys) == len(set(keys)), "Duplicate env_keys found"

    def test_get_field_by_key(self):
        from neurascreen.gui.config.config_fields import get_field
        f = get_field("APP_URL")
        assert f is not None
        assert f.label == "Application URL"
        assert f.required is True

    def test_get_field_unknown(self):
        from neurascreen.gui.config.config_fields import get_field
        assert get_field("NONEXISTENT_KEY") is None

    def test_get_defaults(self):
        from neurascreen.gui.config.config_fields import get_defaults
        defaults = get_defaults()
        assert defaults["APP_URL"] == "http://localhost:3000"
        assert defaults["VIDEO_WIDTH"] == "1920"
        assert defaults["BROWSER_HEADLESS"] == "false"
        assert defaults["TTS_PROVIDER"] == "gradium"

    def test_combo_fields_have_options(self):
        from neurascreen.gui.config.config_fields import FIELDS, TYPE_COMBO
        for f in FIELDS:
            if f.field_type == TYPE_COMBO:
                assert len(f.options) > 0, f"Combo {f.env_key} has no options"

    def test_int_fields_have_ranges(self):
        from neurascreen.gui.config.config_fields import FIELDS, TYPE_INT
        for f in FIELDS:
            if f.field_type == TYPE_INT:
                assert f.max_value > f.min_value, f"Int {f.env_key} has invalid range"


class TestParseEnvFile:
    """Test .env file parsing."""

    def test_parse_simple(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = "APP_URL=http://localhost:3000\nVIDEO_WIDTH=1920\n"
        result = parse_env_file(content)
        assert result["APP_URL"] == "http://localhost:3000"
        assert result["VIDEO_WIDTH"] == "1920"

    def test_parse_ignores_comments(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = "# Comment\nAPP_URL=http://localhost\n# Another\n"
        result = parse_env_file(content)
        assert len(result) == 1
        assert "APP_URL" in result

    def test_parse_ignores_blank_lines(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = "\n\nAPP_URL=http://localhost\n\n"
        result = parse_env_file(content)
        assert len(result) == 1

    def test_parse_quoted_values(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = 'SELECTOR_CANVAS=".react-flow"\nAPP_URL=\'http://localhost\'\n'
        result = parse_env_file(content)
        assert result["SELECTOR_CANVAS"] == ".react-flow"
        assert result["APP_URL"] == "http://localhost"

    def test_parse_value_with_equals(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = "SELECTOR=button[title=\"zoom out\"]\n"
        result = parse_env_file(content)
        assert result["SELECTOR"] == 'button[title="zoom out"]'

    def test_parse_empty_value(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        content = "APP_EMAIL=\n"
        result = parse_env_file(content)
        assert result["APP_EMAIL"] == ""

    def test_parse_empty_content(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        assert parse_env_file("") == {}
        assert parse_env_file("# only comments\n") == {}


class TestBuildEnvContent:
    """Test .env file generation."""

    def test_build_includes_header(self):
        from neurascreen.gui.config.config_fields import build_env_content, get_defaults
        content = build_env_content(get_defaults())
        assert "NeuraScreen" in content
        assert "Configuration Manager" in content

    def test_build_groups_by_tab(self):
        from neurascreen.gui.config.config_fields import build_env_content, get_defaults
        content = build_env_content(get_defaults())
        assert "# --- Application ---" in content
        assert "# --- Browser ---" in content

    def test_build_quotes_values_with_spaces(self):
        from neurascreen.gui.config.config_fields import build_env_content
        values = {"APP_URL": "http://localhost", "LOGIN_EMAIL_SELECTOR": "input[name='email'], input[type='email']"}
        content = build_env_content(values)
        # Should be quoted because of comma+space
        assert 'LOGIN_EMAIL_SELECTOR="input' in content

    def test_build_skips_empty_optional(self):
        from neurascreen.gui.config.config_fields import build_env_content
        values = {"APP_URL": "http://localhost", "APP_EMAIL": "", "APP_PASSWORD": ""}
        content = build_env_content(values)
        assert "APP_URL=" in content
        assert "APP_EMAIL" not in content
        assert "APP_PASSWORD" not in content

    def test_roundtrip(self):
        from neurascreen.gui.config.config_fields import (
            build_env_content, parse_env_file, get_defaults,
        )
        defaults = get_defaults()
        # Set some non-empty values
        values = dict(defaults)
        values["APP_URL"] = "https://app.example.com"
        values["VIDEO_FPS"] = "60"
        values["TTS_PROVIDER"] = "elevenlabs"

        content = build_env_content(values)
        parsed = parse_env_file(content)

        assert parsed["APP_URL"] == "https://app.example.com"
        assert parsed["VIDEO_FPS"] == "60"
        assert parsed["TTS_PROVIDER"] == "elevenlabs"


class TestValidation:
    """Test field validation."""

    def test_valid_defaults(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        errors = validate_values(get_defaults())
        assert errors == []

    def test_required_field_empty(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["APP_URL"] = ""
        errors = validate_values(values)
        assert any("required" in e.lower() for e in errors)

    def test_invalid_url(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["APP_URL"] = "not-a-url"
        errors = validate_values(values)
        assert any("http" in e.lower() for e in errors)

    def test_invalid_int(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["VIDEO_WIDTH"] = "abc"
        errors = validate_values(values)
        assert any("number" in e.lower() for e in errors)

    def test_int_out_of_range(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["VIDEO_FPS"] = "999"
        errors = validate_values(values)
        assert any("between" in e.lower() for e in errors)

    def test_invalid_combo(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["TTS_PROVIDER"] = "invalid_provider"
        errors = validate_values(values)
        assert any("must be one of" in e.lower() for e in errors)

    def test_valid_custom_values(self):
        from neurascreen.gui.config.config_fields import validate_values, get_defaults
        values = get_defaults()
        values["APP_URL"] = "https://app.neurascope.ai"
        values["VIDEO_FPS"] = "60"
        values["TTS_PROVIDER"] = "openai"
        errors = validate_values(values)
        assert errors == []


class TestFileOperations:
    """Test reading/writing .env files."""

    def test_write_and_read_back(self):
        from neurascreen.gui.config.config_fields import (
            build_env_content, parse_env_file, get_defaults,
        )
        values = get_defaults()
        values["APP_URL"] = "https://test.example.com"
        values["TTS_API_KEY"] = "sk-test-key-123"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            content = build_env_content(values)
            f.write(content)
            f.flush()

            read_content = Path(f.name).read_text(encoding="utf-8")
            parsed = parse_env_file(read_content)

            assert parsed["APP_URL"] == "https://test.example.com"
            assert parsed["TTS_API_KEY"] == "sk-test-key-123"

            Path(f.name).unlink()

    def test_read_nonexistent_file(self):
        from neurascreen.gui.config.config_fields import parse_env_file
        # parse_env_file works on content strings, not file paths
        # A nonexistent file would be handled by the dialog's _load_from_file
        assert parse_env_file("") == {}


class TestConfigDialogImport:
    """Test dialog import (pure logic only)."""

    def test_import_exists(self):
        from neurascreen.gui.config.config_dialog import ConfigDialog
        assert ConfigDialog is not None
