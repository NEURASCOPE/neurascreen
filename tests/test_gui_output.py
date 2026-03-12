"""Tests for output browser — pure logic, no Qt dependency."""

import tempfile
from pathlib import Path


class TestParseSRT:
    """Test SRT file parsing."""

    def test_parse_simple(self):
        from neurascreen.gui.output.viewers import parse_srt
        content = """1
00:00:05,000 --> 00:00:10,000
Hello world

2
00:00:15,000 --> 00:00:20,000
Second subtitle
"""
        entries = parse_srt(content)
        assert len(entries) == 2
        assert entries[0].index == 1
        assert entries[0].start == "00:00:05,000"
        assert entries[0].end == "00:00:10,000"
        assert entries[0].text == "Hello world"
        assert entries[1].index == 2
        assert entries[1].text == "Second subtitle"

    def test_parse_multiline_text(self):
        from neurascreen.gui.output.viewers import parse_srt
        content = """1
00:00:00,000 --> 00:00:05,000
Line one
Line two
"""
        entries = parse_srt(content)
        assert len(entries) == 1
        assert "Line one\nLine two" == entries[0].text

    def test_parse_empty(self):
        from neurascreen.gui.output.viewers import parse_srt
        assert parse_srt("") == []
        assert parse_srt("   ") == []

    def test_parse_invalid_blocks(self):
        from neurascreen.gui.output.viewers import parse_srt
        content = """not a number
bad time
some text

2
00:00:01,000 --> 00:00:02,000
Valid entry
"""
        entries = parse_srt(content)
        assert len(entries) == 1
        assert entries[0].index == 2


class TestParseChapters:
    """Test chapters file parsing."""

    def test_parse_simple(self):
        from neurascreen.gui.output.viewers import parse_chapters
        content = """00:00 Introduction
01:30 First section
03:45 Conclusion
"""
        chapters = parse_chapters(content)
        assert len(chapters) == 3
        assert chapters[0].timestamp == "00:00"
        assert chapters[0].title == "Introduction"
        assert chapters[1].timestamp == "01:30"
        assert chapters[2].title == "Conclusion"

    def test_parse_with_hours(self):
        from neurascreen.gui.output.viewers import parse_chapters
        content = "1:00:00 Long video section\n"
        chapters = parse_chapters(content)
        assert len(chapters) == 1
        assert chapters[0].timestamp == "1:00:00"

    def test_parse_empty(self):
        from neurascreen.gui.output.viewers import parse_chapters
        assert parse_chapters("") == []
        assert parse_chapters("\n\n") == []

    def test_parse_ignores_invalid_lines(self):
        from neurascreen.gui.output.viewers import parse_chapters
        content = """Some random text
00:00 Valid chapter
Another invalid line
02:00 Another chapter
"""
        chapters = parse_chapters(content)
        assert len(chapters) == 2


class TestListOutputFiles:
    """Test output file listing."""

    def test_list_empty_dir(self):
        from neurascreen.gui.output.viewers import list_output_files
        with tempfile.TemporaryDirectory() as d:
            files = list_output_files(Path(d))
            assert files == []

    def test_list_nonexistent_dir(self):
        from neurascreen.gui.output.viewers import list_output_files
        files = list_output_files(Path("/nonexistent/dir"))
        assert files == []

    def test_list_mp4_files(self):
        from neurascreen.gui.output.viewers import list_output_files
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "video1.mp4").write_bytes(b"\x00" * 100)
            (p / "video2.mp4").write_bytes(b"\x00" * 200)
            (p / "not-a-video.txt").write_text("ignored")

            files = list_output_files(p)
            assert len(files) == 2
            names = [f.name for f in files]
            assert "video1.mp4" in names
            assert "video2.mp4" in names

    def test_detects_srt_and_chapters(self):
        from neurascreen.gui.output.viewers import list_output_files
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "demo.mp4").write_bytes(b"\x00" * 100)
            (p / "demo.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
            (p / "demo.chapters.txt").write_text("00:00 Intro\n")

            files = list_output_files(p)
            assert len(files) == 1
            assert files[0].has_srt is True
            assert files[0].has_chapters is True

    def test_no_srt_no_chapters(self):
        from neurascreen.gui.output.viewers import list_output_files
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "solo.mp4").write_bytes(b"\x00" * 50)

            files = list_output_files(p)
            assert files[0].has_srt is False
            assert files[0].has_chapters is False

    def test_detects_youtube(self):
        from neurascreen.gui.output.viewers import list_output_files
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "demo.mp4").write_bytes(b"\x00" * 100)
            (p / "demo.youtube.md").write_text("# Title\n")

            files = list_output_files(p)
            assert files[0].has_youtube is True


class TestOutputFileInfo:
    """Test OutputFileInfo properties."""

    def test_size_human_bytes(self):
        from neurascreen.gui.output.viewers import OutputFileInfo
        info = OutputFileInfo("t.mp4", Path("t.mp4"), 500, 0, False, False, False)
        assert info.size_human == "500 B"

    def test_size_human_kb(self):
        from neurascreen.gui.output.viewers import OutputFileInfo
        info = OutputFileInfo("t.mp4", Path("t.mp4"), 5120, 0, False, False, False)
        assert info.size_human == "5.0 KB"

    def test_size_human_mb(self):
        from neurascreen.gui.output.viewers import OutputFileInfo
        info = OutputFileInfo("t.mp4", Path("t.mp4"), 21 * 1024 * 1024, 0, False, False, False)
        assert info.size_human == "21.0 MB"

    def test_srt_path(self):
        from neurascreen.gui.output.viewers import OutputFileInfo
        info = OutputFileInfo("demo.mp4", Path("/out/demo.mp4"), 0, 0, False, False, False)
        assert info.srt_path == Path("/out/demo.srt")

    def test_chapters_path(self):
        from neurascreen.gui.output.viewers import OutputFileInfo
        info = OutputFileInfo("demo.mp4", Path("/out/demo.mp4"), 0, 0, False, False, False)
        assert info.chapters_path == Path("/out/demo.chapters.txt")


class TestOutputStats:
    """Test output statistics."""

    def test_empty(self):
        from neurascreen.gui.output.viewers import compute_output_stats
        stats = compute_output_stats([])
        assert stats["count"] == 0
        assert stats["total_size"] == 0

    def test_with_files(self):
        from neurascreen.gui.output.viewers import compute_output_stats, OutputFileInfo
        files = [
            OutputFileInfo("a.mp4", Path("a.mp4"), 1000, 0, False, False, False),
            OutputFileInfo("b.mp4", Path("b.mp4"), 2000, 0, True, False, False),
        ]
        stats = compute_output_stats(files)
        assert stats["count"] == 2
        assert stats["total_size"] == 3000


class TestFormatDisplay:
    """Test display formatting."""

    def test_format_srt_display(self):
        from neurascreen.gui.output.viewers import SRTEntry, format_srt_display
        entries = [
            SRTEntry(1, "00:00:00,000", "00:00:05,000", "Hello"),
            SRTEntry(2, "00:00:10,000", "00:00:15,000", "World"),
        ]
        text = format_srt_display(entries)
        assert "00:00:00,000" in text
        assert "Hello" in text
        assert "World" in text

    def test_format_chapters_display(self):
        from neurascreen.gui.output.viewers import Chapter, format_chapters_display
        chapters = [
            Chapter("00:00", "Introduction"),
            Chapter("01:30", "Main"),
        ]
        text = format_chapters_display(chapters)
        assert "00:00" in text
        assert "Introduction" in text
        assert "01:30" in text


class TestOutputBrowser:
    """Test browser import."""

    def test_import(self):
        from neurascreen.gui.output.output_browser import OutputBrowser
        assert OutputBrowser is not None
