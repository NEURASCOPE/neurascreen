"""Tests for video assembler."""

import shutil
import subprocess
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from neurascreen.assembler import Assembler
from neurascreen.config import Config


def _make_config(tmp_path: Path) -> Config:
    """Create a Config pointing to tmp directories."""
    return Config(
        app_url="http://localhost",
        app_email="",
        app_password="",
        login_url="/login",
        output_dir=tmp_path / "output",
        temp_dir=tmp_path / "temp",
        logs_dir=tmp_path / "logs",
        scenarios_dir=tmp_path / "examples",
        browser_headless=True,
        video_width=1920,
        video_height=1080,
        video_fps=30,
        capture_screen=0,
        browser_screen_offset=0,
        tts_provider="gradium",
        tts_api_key="",
        tts_voice_id="",
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


def _create_wav(path: Path, duration_s: float = 1.0, rate: int = 48000) -> Path:
    """Create a valid WAV file."""
    n_frames = int(rate * duration_s)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path


def _create_test_video(path: Path, duration_s: float = 2.0) -> Path:
    """Create a minimal test video via ffmpeg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=320x240:d={duration_s}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"Failed to create test video: {result.stderr}"
    return path


@pytest.fixture
def assembler(tmp_path):
    config = _make_config(tmp_path)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    return Assembler(config)


class TestCheckFfmpeg:
    """Tests for ffmpeg availability check."""

    def test_ffmpeg_available(self, tmp_path):
        config = _make_config(tmp_path)
        Assembler(config)  # Should not raise

    def test_ffmpeg_missing(self, tmp_path):
        config = _make_config(tmp_path)
        with patch.object(shutil, "which", return_value=None):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                Assembler(config)


class TestGetVideoDuration:
    """Tests for get_video_duration()."""

    def test_known_duration(self, tmp_path):
        video = _create_test_video(tmp_path / "test.mp4", duration_s=3.0)
        duration = Assembler.get_video_duration(video)
        assert abs(duration - 3.0) < 0.5

    def test_fallback_estimation(self, tmp_path):
        # Create a dummy file (not a real video)
        fake = tmp_path / "fake.mkv"
        fake.write_bytes(b"\x00" * 500_000)
        duration = Assembler.get_video_duration(fake)
        assert duration > 0


class TestConvertToMp4:
    """Tests for convert_to_mp4()."""

    def test_convert_basic(self, assembler, tmp_path):
        video = _create_test_video(tmp_path / "input.mp4", duration_s=1.0)
        output = assembler.convert_to_mp4(video, output_path=tmp_path / "out.mp4")
        assert output.exists()
        assert output.stat().st_size > 0

    def test_convert_with_name(self, assembler, tmp_path):
        video = _create_test_video(tmp_path / "input.mp4", duration_s=1.0)
        output = assembler.convert_to_mp4(video, output_name="My Demo Video")
        assert output.exists()
        assert "my_demo_video" in output.name

    def test_convert_missing_input(self, assembler, tmp_path):
        with pytest.raises(FileNotFoundError):
            assembler.convert_to_mp4(tmp_path / "nonexistent.mp4")


class TestAssembleWithAudio:
    """Tests for assemble_with_audio()."""

    def test_assemble(self, assembler, tmp_path):
        video = _create_test_video(tmp_path / "video.mp4", duration_s=2.0)
        audio = _create_wav(tmp_path / "audio.wav", duration_s=2.0)
        output = tmp_path / "final.mp4"
        result = assembler.assemble_with_audio(video, audio, output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_assemble_missing_video(self, assembler, tmp_path):
        audio = _create_wav(tmp_path / "audio.wav")
        with pytest.raises(FileNotFoundError, match="Video not found"):
            assembler.assemble_with_audio(tmp_path / "nope.mp4", audio, tmp_path / "out.mp4")

    def test_assemble_missing_audio(self, assembler, tmp_path):
        video = _create_test_video(tmp_path / "video.mp4")
        with pytest.raises(FileNotFoundError, match="Audio not found"):
            assembler.assemble_with_audio(video, tmp_path / "nope.wav", tmp_path / "out.mp4")


class TestCreateSilence:
    """Tests for _create_silence()."""

    def test_creates_wav(self, tmp_path):
        path = tmp_path / "silence.wav"
        Assembler._create_silence(path, 1.0)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_minimum_duration(self, tmp_path):
        path = tmp_path / "tiny.wav"
        Assembler._create_silence(path, 0.001)
        assert path.exists()


class TestGetWavDurationS:
    """Tests for _get_wav_duration_s()."""

    def test_known_duration(self, tmp_path):
        wav = _create_wav(tmp_path / "test.wav", duration_s=2.5)
        duration = Assembler._get_wav_duration_s(wav)
        assert abs(duration - 2.5) < 0.1

    def test_fallback_for_non_wav(self, tmp_path):
        fake = tmp_path / "fake.wav"
        fake.write_bytes(b"\x00" * 96000)  # ~1 second at 48kHz/16bit/mono
        duration = Assembler._get_wav_duration_s(fake)
        assert duration > 0


class TestBuildAudioFromTimestamps:
    """Tests for build_audio_from_timestamps()."""

    def test_empty_timestamps(self, assembler, tmp_path):
        output = assembler.build_audio_from_timestamps([], 5.0)
        assert output.exists()

    def test_single_timestamp(self, assembler, tmp_path):
        wav = _create_wav(tmp_path / "clip.wav", duration_s=1.0)
        output = assembler.build_audio_from_timestamps([(1.0, wav)], 5.0)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_multiple_timestamps(self, assembler, tmp_path):
        wav1 = _create_wav(tmp_path / "clip1.wav", duration_s=1.0)
        wav2 = _create_wav(tmp_path / "clip2.wav", duration_s=1.0)
        timestamps = [(0.5, wav1), (3.0, wav2)]
        output = assembler.build_audio_from_timestamps(timestamps, 6.0)
        assert output.exists()
        assert output.stat().st_size > 0


class TestCleanupTemp:
    """Tests for cleanup_temp()."""

    def test_cleans_video_dir(self, assembler):
        video_dir = assembler.config.temp_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        (video_dir / "test.mkv").write_bytes(b"fake")
        assembler.cleanup_temp()
        assert list(video_dir.iterdir()) == []

    def test_no_error_if_empty(self, assembler):
        assembler.cleanup_temp()  # Should not raise
