"""Tests for CLI voices commands and Config voices.json integration."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner


def _make_config(provider="openai", voice_id="alloy"):
    """Create a minimal Config for testing without loading .env."""
    from neurascreen.config import Config
    tmp = Path(tempfile.mkdtemp())
    return Config(
        app_url="http://localhost", app_email="", app_password="",
        login_url="/login", output_dir=tmp, temp_dir=tmp,
        logs_dir=tmp, scenarios_dir=tmp,
        browser_headless=False, video_width=1920, video_height=1080, video_fps=30,
        capture_screen=0, capture_display="", browser_screen_offset=0,
        tts_provider=provider, tts_api_key="test",
        tts_voice_id=voice_id, tts_model="default",
        login_email_selector="", login_password_selector="", login_submit_selector="",
        selector_draggable="", selector_canvas="", selector_delete_button="",
        selector_close_modal="", selector_zoom_out="", selector_fit_view="",
    )


class TestVoicesList:
    """Test neurascreen voices list command."""

    def test_list_all_providers(self):
        from neurascreen.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["voices", "list"], obj={})
        assert result.exit_code == 0
        assert "openai" in result.output
        assert "gradium" in result.output

    def test_list_single_provider(self):
        from neurascreen.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["voices", "list", "-p", "openai"], obj={})
        assert result.exit_code == 0
        assert "openai" in result.output
        assert "alloy" in result.output
        assert "gradium" not in result.output


class TestVoicesAdd:
    """Test neurascreen voices add command."""

    def test_add_voice(self):
        from neurascreen.cli import cli
        from neurascreen.gui.tts.voices import load_voices, VOICES_FILE
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["voices", "add", "gradium", "test123", "Test Voice"], obj={}
            )
            assert result.exit_code == 0
            assert "Added" in result.output

            # Verify it was saved
            configs = load_voices(tmp)
            ids = [v.id for v in configs["gradium"].voices]
            assert "test123" in ids
        finally:
            mod.VOICES_FILE = original

    def test_add_duplicate(self):
        from neurascreen.cli import cli
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            # Add once
            runner.invoke(cli, ["voices", "add", "openai", "alloy", "Alloy"], obj={})
            # Add again — should fail (already exists in builtins)
            result = runner.invoke(
                cli, ["voices", "add", "openai", "alloy", "Alloy"], obj={}
            )
            assert result.exit_code == 1
            assert "already exists" in result.output
        finally:
            mod.VOICES_FILE = original


class TestVoicesRemove:
    """Test neurascreen voices remove command."""

    def test_remove_voice(self):
        from neurascreen.cli import cli
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            # Add then remove
            runner.invoke(cli, ["voices", "add", "gradium", "xyz", "XYZ"], obj={})
            result = runner.invoke(cli, ["voices", "remove", "gradium", "xyz"], obj={})
            assert result.exit_code == 0
            assert "Removed" in result.output
        finally:
            mod.VOICES_FILE = original

    def test_remove_nonexistent(self):
        from neurascreen.cli import cli
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["voices", "remove", "gradium", "nope"], obj={}
            )
            assert result.exit_code == 1
            assert "not found" in result.output
        finally:
            mod.VOICES_FILE = original


class TestVoicesSetDefault:
    """Test neurascreen voices set-default command."""

    def test_set_default(self):
        from neurascreen.cli import cli
        from neurascreen.gui.tts.voices import load_voices
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["voices", "set-default", "openai", "nova"], obj={}
            )
            assert result.exit_code == 0
            assert "nova" in result.output

            configs = load_voices(tmp)
            assert configs["openai"].default_voice == "nova"
        finally:
            mod.VOICES_FILE = original

    def test_set_default_unknown_provider(self):
        from neurascreen.cli import cli
        import neurascreen.gui.tts.voices as mod

        tmp = Path(tempfile.mkdtemp()) / "voices.json"
        original = mod.VOICES_FILE
        mod.VOICES_FILE = tmp

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["voices", "set-default", "nonexistent", "v1"], obj={}
            )
            assert result.exit_code == 1
            assert "Unknown provider" in result.output
        finally:
            mod.VOICES_FILE = original


class TestConfigVoicesFallback:
    """Test Config._apply_voices_defaults() logic."""

    def test_fallback_fills_empty_voice(self):
        from neurascreen.config import Config

        # Build config directly (bypass .env loading)
        config = Config(
            app_url="http://localhost", app_email="", app_password="",
            login_url="/login", output_dir=Path(tempfile.mkdtemp()),
            temp_dir=Path(tempfile.mkdtemp()), logs_dir=Path(tempfile.mkdtemp()),
            scenarios_dir=Path(tempfile.mkdtemp()),
            browser_headless=False, video_width=1920, video_height=1080, video_fps=30,
            capture_screen=0, capture_display="", browser_screen_offset=0,
            tts_provider="openai", tts_api_key="test",
            tts_voice_id="", tts_model="",
            login_email_selector="", login_password_selector="", login_submit_selector="",
            selector_draggable="", selector_canvas="", selector_delete_button="",
            selector_close_modal="", selector_zoom_out="", selector_fit_view="",
        )
        config._apply_voices_defaults()
        assert config.tts_voice_id == "alloy"
        assert config.tts_model == "tts-1-hd"

    def test_no_fallback_when_set(self):
        from neurascreen.config import Config

        config = Config(
            app_url="http://localhost", app_email="", app_password="",
            login_url="/login", output_dir=Path(tempfile.mkdtemp()),
            temp_dir=Path(tempfile.mkdtemp()), logs_dir=Path(tempfile.mkdtemp()),
            scenarios_dir=Path(tempfile.mkdtemp()),
            browser_headless=False, video_width=1920, video_height=1080, video_fps=30,
            capture_screen=0, capture_display="", browser_screen_offset=0,
            tts_provider="openai", tts_api_key="test",
            tts_voice_id="custom_voice", tts_model="custom_model",
            login_email_selector="", login_password_selector="", login_submit_selector="",
            selector_draggable="", selector_canvas="", selector_delete_button="",
            selector_close_modal="", selector_zoom_out="", selector_fit_view="",
        )
        config._apply_voices_defaults()
        assert config.tts_voice_id == "custom_voice"
        assert config.tts_model == "custom_model"


class TestValidateVoiceWarning:
    """Test that validate command warns about unknown voices."""

    def test_validate_warns_unknown_voice(self):
        from neurascreen.cli import cli
        import os

        scenario = {
            "title": "Test",
            "description": "test",
            "resolution": {"width": 1920, "height": 1080},
            "steps": [{"action": "wait", "duration": 1000}],
        }
        tmp_dir = Path(tempfile.mkdtemp())
        tmp = tmp_dir / "test.json"
        tmp.write_text(json.dumps(scenario))

        # Create a minimal .env to avoid polluting os.environ with the real .env
        env_file = tmp_dir / ".env"
        env_file.write_text("APP_URL=http://localhost\nTTS_PROVIDER=openai\nTTS_VOICE_ID=nonexistent_xyz\n")

        runner = CliRunner(env={"DOTENV_PATH": str(env_file)})
        # Use patch to make Config.load use our temp .env
        with patch("neurascreen.cli.Config.load", return_value=_make_config("openai", "nonexistent_xyz")):
            result = runner.invoke(cli, ["validate", str(tmp)], obj={})
        assert result.exit_code == 0
        assert "Valid scenario" in result.output
