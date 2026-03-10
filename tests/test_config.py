"""Tests for configuration loader."""

import os
import tempfile
from pathlib import Path

import pytest

from neurascreen.config import Config


class TestConfig:
    """Tests for Config.load()."""

    def test_load_defaults(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://test:3000\n")

        config = Config.load(str(env_file))
        assert config.app_url == "http://test:3000"
        assert config.login_url == "/login"
        assert config.browser_headless is False
        assert config.video_width == 1920
        assert config.video_height == 1080
        assert config.video_fps == 30
        assert config.capture_screen == 0
        assert config.browser_screen_offset == 0
        assert config.tts_provider == "gradium"

    def test_load_custom_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_URL=http://myapp:8080\n"
            "APP_EMAIL=user@test.com\n"
            "APP_PASSWORD=secret\n"
            "LOGIN_URL=/auth/login\n"
            "VIDEO_WIDTH=1280\n"
            "VIDEO_HEIGHT=720\n"
            "TTS_PROVIDER=openai\n"
            "TTS_API_KEY=sk-test\n"
            "TTS_VOICE_ID=nova\n"
        )

        config = Config.load(str(env_file))
        assert config.app_url == "http://myapp:8080"
        assert config.app_email == "user@test.com"
        assert config.app_password == "secret"
        assert config.login_url == "/auth/login"
        assert config.video_width == 1280
        assert config.video_height == 720
        assert config.tts_provider == "openai"
        assert config.tts_api_key == "sk-test"
        assert config.tts_voice_id == "nova"

    def test_validate_ok(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://localhost\n")

        config = Config.load(str(env_file))
        assert config.validate() == []

    def test_validate_tts_missing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://localhost\nTTS_API_KEY=\n")

        config = Config.load(str(env_file))
        errors = config.validate_tts()
        assert any("TTS_API_KEY" in e for e in errors)

    def test_url_trailing_slash_stripped(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://localhost:3000/\n")

        config = Config.load(str(env_file))
        assert config.app_url == "http://localhost:3000"

    def test_login_selector_defaults(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://localhost\n")

        config = Config.load(str(env_file))
        assert "email" in config.login_email_selector
        assert "password" in config.login_password_selector
        assert "submit" in config.login_submit_selector

    def test_login_selector_custom(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_URL=http://localhost\n"
            "LOGIN_EMAIL_SELECTOR=#username\n"
            "LOGIN_PASSWORD_SELECTOR=#passwd\n"
            "LOGIN_SUBMIT_SELECTOR=#login-btn\n"
        )

        config = Config.load(str(env_file))
        assert config.login_email_selector == "#username"
        assert config.login_password_selector == "#passwd"
        assert config.login_submit_selector == "#login-btn"

    def test_canvas_selector_defaults(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("APP_URL=http://localhost\n")

        config = Config.load(str(env_file))
        assert config.selector_draggable == "[draggable='true']"
        assert config.selector_canvas == ".react-flow"
        assert "Delete" in config.selector_delete_button
        assert "zoom out" in config.selector_zoom_out
        assert "fit view" in config.selector_fit_view

    def test_canvas_selector_custom(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_URL=http://localhost\n"
            "SELECTOR_CANVAS=.my-canvas\n"
            "SELECTOR_DRAGGABLE=.drag-item\n"
            "SELECTOR_ZOOM_OUT=#zoom-minus\n"
        )

        config = Config.load(str(env_file))
        assert config.selector_canvas == ".my-canvas"
        assert config.selector_draggable == ".drag-item"
        assert config.selector_zoom_out == "#zoom-minus"
