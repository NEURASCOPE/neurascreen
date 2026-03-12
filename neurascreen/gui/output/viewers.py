"""SRT and chapters viewers — parse and display subtitle/chapter files.

Pure parsing logic is Qt-free and testable. Viewer widgets use Qt.
"""

import re
from dataclasses import dataclass
from pathlib import Path


# ------------------------------------------------------------------ #
#  Data structures (pure Python)                                      #
# ------------------------------------------------------------------ #

@dataclass
class SRTEntry:
    """A single SRT subtitle entry."""

    index: int
    start: str  # HH:MM:SS,mmm
    end: str
    text: str


@dataclass
class Chapter:
    """A single chapter marker."""

    timestamp: str  # MM:SS or HH:MM:SS
    title: str


@dataclass
class OutputFileInfo:
    """Metadata about an output file group (MP4 + optional SRT/chapters)."""

    name: str
    path: Path
    size_bytes: int
    modified: float  # timestamp
    has_srt: bool
    has_chapters: bool
    has_youtube: bool

    @property
    def size_human(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / (1024 * 1024):.1f} MB"

    @property
    def srt_path(self) -> Path:
        return self.path.with_suffix(".srt")

    @property
    def chapters_path(self) -> Path:
        return self.path.parent / f"{self.path.stem}.chapters.txt"

    @property
    def youtube_path(self) -> Path:
        return self.path.parent / f"{self.path.stem}.youtube.md"


# ------------------------------------------------------------------ #
#  Parsing (pure Python, no Qt)                                       #
# ------------------------------------------------------------------ #

def parse_srt(content: str) -> list[SRTEntry]:
    """Parse SRT file content into a list of entries."""
    entries = []
    blocks = re.split(r"\n\n+", content.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1].strip(),
        )
        if not time_match:
            continue
        text = "\n".join(lines[2:]).strip()
        entries.append(SRTEntry(
            index=index,
            start=time_match.group(1),
            end=time_match.group(2),
            text=text,
        ))
    return entries


def parse_chapters(content: str) -> list[Chapter]:
    """Parse chapters file content into a list of chapters."""
    chapters = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)", line)
        if match:
            chapters.append(Chapter(
                timestamp=match.group(1),
                title=match.group(2).strip(),
            ))
    return chapters


def list_output_files(output_dir: Path) -> list[OutputFileInfo]:
    """List MP4 files in the output directory with metadata."""
    if not output_dir.exists():
        return []

    files = []
    for mp4 in sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = mp4.stat()
        stem = mp4.stem
        files.append(OutputFileInfo(
            name=mp4.name,
            path=mp4,
            size_bytes=stat.st_size,
            modified=stat.st_mtime,
            has_srt=(mp4.parent / f"{stem}.srt").exists(),
            has_chapters=(mp4.parent / f"{stem}.chapters.txt").exists(),
            has_youtube=(mp4.parent / f"{stem}.youtube.md").exists(),
        ))
    return files


def compute_output_stats(files: list[OutputFileInfo]) -> dict:
    """Compute summary stats for output files."""
    total_size = sum(f.size_bytes for f in files)
    return {
        "count": len(files),
        "total_size": total_size,
        "total_size_human": _human_size(total_size),
    }


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_srt_display(entries: list[SRTEntry]) -> str:
    """Format SRT entries for display."""
    lines = []
    for e in entries:
        lines.append(f"[{e.start} → {e.end}]")
        lines.append(e.text)
        lines.append("")
    return "\n".join(lines)


def format_chapters_display(chapters: list[Chapter]) -> str:
    """Format chapters for display."""
    lines = []
    for ch in chapters:
        lines.append(f"{ch.timestamp}  {ch.title}")
    return "\n".join(lines)
