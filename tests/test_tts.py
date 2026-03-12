"""Tests for TTS abstraction."""

import struct
import wave
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from neurascreen.tts import (
    create_tts_client,
    get_wav_duration_ms,
    GradiumTTSClient,
    ElevenLabsTTSClient,
    OpenAITTSClient,
    GoogleTTSClient,
    CoquiTTSClient,
)
from neurascreen.config import Config


def _make_config(provider: str = "gradium", **overrides) -> Config:
    """Create a Config with TTS settings."""
    defaults = dict(
        app_url="http://localhost",
        app_email="",
        app_password="",
        login_url="/login",
        output_dir=Path("/tmp/test-output"),
        temp_dir=Path("/tmp/test-temp"),
        logs_dir=Path("/tmp/test-logs"),
        scenarios_dir=Path("/tmp/test-scenarios"),
        browser_headless=True,
        video_width=1920,
        video_height=1080,
        video_fps=30,
        capture_screen=0,
        capture_display="",
        browser_screen_offset=0,
        tts_provider=provider,
        tts_api_key="test-key",
        tts_voice_id="test-voice",
        tts_model="default",
        login_email_selector="input[name='email']",
        login_password_selector="input[name='password']",
        login_submit_selector="button[type='submit']",
        selector_draggable="[draggable='true']",
        selector_canvas=".react-flow",
        selector_delete_button='button[title="Delete"]',
        selector_close_modal='[role="dialog"] button:has-text("Close")',
        selector_zoom_out='button[title="zoom out"]',
        selector_fit_view='button[title="fit view"]',
    )
    defaults.update(overrides)
    return Config(**defaults)


class TestCreateTTSClient:
    """Tests for TTS factory."""

    def test_gradium(self):
        config = _make_config("gradium")
        client = create_tts_client(config)
        assert isinstance(client, GradiumTTSClient)

    def test_elevenlabs(self):
        config = _make_config("elevenlabs")
        client = create_tts_client(config)
        assert isinstance(client, ElevenLabsTTSClient)

    def test_eleven_labs_alias(self):
        config = _make_config("eleven_labs")
        client = create_tts_client(config)
        assert isinstance(client, ElevenLabsTTSClient)

    def test_openai(self):
        config = _make_config("openai")
        client = create_tts_client(config)
        assert isinstance(client, OpenAITTSClient)

    def test_google(self):
        config = _make_config("google")
        client = create_tts_client(config)
        assert isinstance(client, GoogleTTSClient)

    def test_google_cloud_alias(self):
        config = _make_config("google_cloud")
        client = create_tts_client(config)
        assert isinstance(client, GoogleTTSClient)

    def test_coqui(self):
        config = _make_config("coqui")
        client = create_tts_client(config)
        assert isinstance(client, CoquiTTSClient)

    def test_unknown_provider(self):
        config = _make_config("unknown_provider")
        with pytest.raises(ValueError, match="Unknown TTS provider"):
            create_tts_client(config)


class TestGetWavDuration:
    """Tests for get_wav_duration_ms()."""

    def _create_wav(self, tmp_path: Path, duration_s: float, rate: int = 48000) -> Path:
        """Create a valid WAV file with known duration."""
        path = tmp_path / "test.wav"
        n_frames = int(rate * duration_s)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(rate)
            wf.writeframes(b"\x00\x00" * n_frames)
        return path

    def test_known_duration(self, tmp_path):
        wav = self._create_wav(tmp_path, 2.0)
        duration = get_wav_duration_ms(wav)
        assert abs(duration - 2000) < 50  # ~2000ms with small tolerance

    def test_short_file(self, tmp_path):
        wav = self._create_wav(tmp_path, 0.5)
        duration = get_wav_duration_ms(wav)
        assert abs(duration - 500) < 50

    def test_five_seconds(self, tmp_path):
        wav = self._create_wav(tmp_path, 5.0)
        duration = get_wav_duration_ms(wav)
        assert abs(duration - 5000) < 50
