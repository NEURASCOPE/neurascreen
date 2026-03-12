"""Tests for subtitle (SRT) and YouTube chapter generation."""

import wave
from pathlib import Path

import pytest

from neurascreen.subtitles import (
    _format_srt_time,
    _format_chapter_time,
    generate_srt,
    generate_chapters,
)


def _create_wav(path: Path, duration_s: float = 1.0, rate: int = 48000) -> Path:
    """Create a valid WAV file with the given duration."""
    n_frames = int(rate * duration_s)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path


class TestFormatSrtTime:
    """Tests for SRT timestamp formatting."""

    def test_zero(self):
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_seconds_only(self):
        assert _format_srt_time(5.5) == "00:00:05,500"

    def test_minutes(self):
        assert _format_srt_time(65.123) == "00:01:05,123"

    def test_hours(self):
        assert _format_srt_time(3661.0) == "01:01:01,000"

    def test_millis_precision(self):
        assert _format_srt_time(1.999) == "00:00:01,999"


class TestFormatChapterTime:
    """Tests for YouTube chapter timestamp formatting."""

    def test_zero(self):
        assert _format_chapter_time(0.0) == "00:00"

    def test_minutes(self):
        assert _format_chapter_time(125.0) == "02:05"

    def test_hours(self):
        assert _format_chapter_time(3661.0) == "01:01:01"

    def test_no_hours_prefix(self):
        # Under 1 hour should use MM:SS format
        assert _format_chapter_time(59.0) == "00:59"


class TestGenerateSrt:
    """Tests for SRT file generation."""

    def test_basic_srt(self, tmp_path):
        wav1 = _create_wav(tmp_path / "audio" / "step1.wav", 2.0)
        wav2 = _create_wav(tmp_path / "audio" / "step2.wav", 3.0)

        timestamps = [(5.0, wav1), (10.0, wav2)]
        narrations = {0: "First narration.", 3: "Second narration."}
        output = tmp_path / "output.srt"

        result = generate_srt(timestamps, narrations, output)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "1\n" in content
        assert "2\n" in content
        assert "First narration." in content
        assert "Second narration." in content
        assert "-->" in content

    def test_empty_timestamps(self, tmp_path):
        output = tmp_path / "output.srt"
        result = generate_srt([], {}, output)
        assert result.exists()
        assert result.read_text(encoding="utf-8") == ""

    def test_srt_timing_format(self, tmp_path):
        wav = _create_wav(tmp_path / "step.wav", 1.5)
        timestamps = [(2.0, wav)]
        narrations = {0: "Test."}
        output = tmp_path / "output.srt"

        generate_srt(timestamps, narrations, output)
        content = output.read_text(encoding="utf-8")

        assert "00:00:02,000 --> 00:00:03,500" in content

    def test_srt_entry_count(self, tmp_path):
        wavs = [_create_wav(tmp_path / f"s{i}.wav", 1.0) for i in range(5)]
        timestamps = [(i * 3.0, w) for i, w in enumerate(wavs)]
        narrations = {i: f"Narration {i}" for i in range(5)}
        output = tmp_path / "output.srt"

        generate_srt(timestamps, narrations, output)
        content = output.read_text(encoding="utf-8")

        # Count subtitle entries (each starts with a number on its own line)
        entries = [line for line in content.strip().split("\n") if line.strip().isdigit()]
        assert len(entries) == 5

    def test_creates_parent_dir(self, tmp_path):
        wav = _create_wav(tmp_path / "audio.wav", 1.0)
        output = tmp_path / "deep" / "nested" / "output.srt"
        generate_srt([(1.0, wav)], {0: "Test."}, output)
        assert output.exists()


class TestGenerateChapters:
    """Tests for YouTube chapter marker generation."""

    def test_basic_chapters(self, tmp_path):
        wav1 = _create_wav(tmp_path / "s1.wav", 1.0)
        wav2 = _create_wav(tmp_path / "s2.wav", 1.0)

        timestamps = [(5.0, wav1), (30.0, wav2)]
        titles = ["Dashboard Overview", "Settings Page"]
        output = tmp_path / "chapters.txt"

        result = generate_chapters(timestamps, titles, output)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # First chapter should be at 00:00 (auto-inserted Introduction)
        assert lines[0] == "00:00 Introduction"
        assert "00:05 Dashboard Overview" in content
        assert "00:30 Settings Page" in content

    def test_chapter_at_zero_no_extra_intro(self, tmp_path):
        wav = _create_wav(tmp_path / "s.wav", 1.0)

        timestamps = [(0.0, wav)]
        titles = ["Intro"]
        output = tmp_path / "chapters.txt"

        generate_chapters(timestamps, titles, output)
        content = output.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # Should NOT add extra Introduction since first chapter is at 0
        assert len(lines) == 1
        assert lines[0] == "00:00 Intro"

    def test_empty_title_gets_default(self, tmp_path):
        wav = _create_wav(tmp_path / "s.wav", 1.0)

        timestamps = [(5.0, wav)]
        titles = [""]
        output = tmp_path / "chapters.txt"

        generate_chapters(timestamps, titles, output)
        content = output.read_text(encoding="utf-8")

        assert "Section 1" in content

    def test_empty_timestamps(self, tmp_path):
        output = tmp_path / "chapters.txt"
        generate_chapters([], [], output)
        # File may or may not exist, but no crash
        assert True

    def test_more_timestamps_than_titles(self, tmp_path):
        wavs = [_create_wav(tmp_path / f"s{i}.wav", 1.0) for i in range(3)]
        timestamps = [(i * 10.0, w) for i, w in enumerate(wavs)]
        titles = ["Only One"]
        output = tmp_path / "chapters.txt"

        generate_chapters(timestamps, titles, output)
        content = output.read_text(encoding="utf-8")

        # First timestamp is at 0.0, so no extra Introduction inserted
        # Should only generate chapters for available titles
        lines = [l for l in content.strip().split("\n") if l.strip()]
        assert len(lines) == 1
        assert "Only One" in lines[0]

    def test_creates_parent_dir(self, tmp_path):
        wav = _create_wav(tmp_path / "s.wav", 1.0)
        output = tmp_path / "deep" / "nested" / "chapters.txt"
        generate_chapters([(1.0, wav)], ["Test"], output)
        assert output.exists()

    def test_hour_format(self, tmp_path):
        wav = _create_wav(tmp_path / "s.wav", 1.0)
        timestamps = [(3700.0, wav)]
        titles = ["Late Chapter"]
        output = tmp_path / "chapters.txt"

        generate_chapters(timestamps, titles, output)
        content = output.read_text(encoding="utf-8")

        assert "01:01:40 Late Chapter" in content
