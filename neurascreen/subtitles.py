"""Subtitle (SRT) and YouTube chapter marker generation."""

import logging
from pathlib import Path

from .tts import get_wav_duration_ms

logger = logging.getLogger("videogen")


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_chapter_time(seconds: float) -> str:
    """Format seconds to YouTube chapter timestamp: HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_srt(
    audio_timestamps: list[tuple[float, Path]],
    narrations: dict[int, str],
    output_path: Path,
) -> Path:
    """Generate an SRT subtitle file from audio timestamps and narration texts.

    Args:
        audio_timestamps: List of (seconds_from_start, wav_path) tuples.
        narrations: Map of step_index -> narration text.
        output_path: Path for the output .srt file.

    Returns:
        Path to the generated SRT file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build subtitle entries: match timestamps with narration texts
    # narrations keys are step indices, audio_timestamps are ordered by time
    narration_texts = list(narrations.values())
    entries = []

    for i, (start_s, wav_path) in enumerate(audio_timestamps):
        if i >= len(narration_texts):
            break
        duration_ms = get_wav_duration_ms(wav_path)
        end_s = start_s + duration_ms / 1000
        text = narration_texts[i]
        entries.append((start_s, end_s, text))

    with open(output_path, "w", encoding="utf-8") as f:
        for idx, (start_s, end_s, text) in enumerate(entries, 1):
            f.write(f"{idx}\n")
            f.write(f"{_format_srt_time(start_s)} --> {_format_srt_time(end_s)}\n")
            f.write(f"{text}\n")
            f.write("\n")

    logger.info(f"SRT subtitles: {output_path} ({len(entries)} entries)")
    return output_path


def generate_chapters(
    audio_timestamps: list[tuple[float, Path]],
    step_titles: list[str],
    output_path: Path,
) -> Path:
    """Generate a YouTube chapter markers file from timestamps and step titles.

    The output format is one chapter per line: "MM:SS Title"
    YouTube requires the first chapter to start at 00:00.

    Args:
        audio_timestamps: List of (seconds_from_start, wav_path) tuples.
        step_titles: Titles corresponding to each narrated step.
        output_path: Path for the output .chapters.txt file.

    Returns:
        Path to the generated chapters file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chapters = []
    for i, (start_s, _) in enumerate(audio_timestamps):
        if i >= len(step_titles):
            break
        title = step_titles[i].strip()
        if not title:
            title = f"Section {i + 1}"
        chapters.append((start_s, title))

    if not chapters:
        logger.info("No chapters to generate")
        return output_path

    # YouTube requires first chapter at 00:00
    if chapters[0][0] > 0.5:
        chapters.insert(0, (0.0, "Introduction"))

    with open(output_path, "w", encoding="utf-8") as f:
        for start_s, title in chapters:
            f.write(f"{_format_chapter_time(start_s)} {title}\n")

    logger.info(f"YouTube chapters: {output_path} ({len(chapters)} chapters)")
    return output_path
