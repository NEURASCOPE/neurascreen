"""Tests for platform detection and OS-specific command builders."""

from unittest.mock import patch, MagicMock

import pytest

from neurascreen.platform import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    check_audio_dependencies,
    check_capture_dependencies,
    get_audio_play_command,
    get_capture_command,
    get_platform,
    get_platform_name,
    is_linux,
    is_macos,
    is_windows,
)


class TestPlatformDetection:
    """Tests for platform detection functions."""

    def test_get_platform_returns_string(self):
        assert isinstance(get_platform(), str)

    @patch("neurascreen.platform.sys")
    def test_is_macos(self, mock_sys):
        mock_sys.platform = "darwin"
        assert is_macos()
        assert not is_linux()
        assert not is_windows()

    @patch("neurascreen.platform.sys")
    def test_is_linux(self, mock_sys):
        mock_sys.platform = "linux"
        assert is_linux()
        assert not is_macos()
        assert not is_windows()

    @patch("neurascreen.platform.sys")
    def test_is_windows(self, mock_sys):
        mock_sys.platform = "win32"
        assert is_windows()
        assert not is_macos()
        assert not is_linux()

    @patch("neurascreen.platform.sys")
    def test_platform_name_macos(self, mock_sys):
        mock_sys.platform = "darwin"
        assert get_platform_name() == "macOS"

    @patch("neurascreen.platform.sys")
    def test_platform_name_linux(self, mock_sys):
        mock_sys.platform = "linux"
        assert get_platform_name() == "Linux"

    @patch("neurascreen.platform.sys")
    def test_platform_name_windows(self, mock_sys):
        mock_sys.platform = "win32"
        assert get_platform_name() == "Windows"

    @patch("neurascreen.platform.sys")
    def test_platform_name_unknown(self, mock_sys):
        mock_sys.platform = "freebsd"
        assert "Unknown" in get_platform_name()


class TestCaptureCommand:
    """Tests for get_capture_command()."""

    @patch("neurascreen.platform.sys")
    def test_macos_avfoundation(self, mock_sys):
        mock_sys.platform = "darwin"
        cmd = get_capture_command("/tmp/out.mkv", 30, 1)
        assert "avfoundation" in cmd
        assert "-framerate" in cmd
        assert "1:none" in cmd
        assert cmd[0] == "ffmpeg"
        assert cmd[-1] == "/tmp/out.mkv"

    @patch("neurascreen.platform.sys")
    def test_macos_capture_screen_index(self, mock_sys):
        mock_sys.platform = "darwin"
        cmd = get_capture_command("/tmp/out.mkv", 60, 2)
        assert "2:none" in cmd
        assert "60" in cmd

    @patch("neurascreen.platform.sys")
    def test_linux_x11grab(self, mock_sys):
        mock_sys.platform = "linux"
        cmd = get_capture_command("/tmp/out.mkv", 30, 0)
        assert "x11grab" in cmd
        assert ":0.0" in cmd
        assert "-draw_mouse" in cmd

    @patch("neurascreen.platform.sys")
    def test_linux_custom_display(self, mock_sys):
        mock_sys.platform = "linux"
        cmd = get_capture_command("/tmp/out.mkv", 30, 0, capture_display=":1.0+100,200")
        assert ":1.0+100,200" in cmd

    @patch("neurascreen.platform.sys")
    def test_linux_default_display(self, mock_sys):
        mock_sys.platform = "linux"
        cmd = get_capture_command("/tmp/out.mkv", 30, 0, capture_display="")
        assert ":0.0" in cmd

    @patch("neurascreen.platform.sys")
    def test_windows_gdigrab(self, mock_sys):
        mock_sys.platform = "win32"
        cmd = get_capture_command("/tmp/out.mkv", 30, 0)
        assert "gdigrab" in cmd
        assert "desktop" in cmd
        assert "-draw_mouse" in cmd

    @patch("neurascreen.platform.sys")
    def test_windows_custom_input(self, mock_sys):
        mock_sys.platform = "win32"
        cmd = get_capture_command("/tmp/out.mkv", 30, 0, capture_display="title=MyApp")
        assert "title=MyApp" in cmd

    @patch("neurascreen.platform.sys")
    def test_unsupported_platform_raises(self, mock_sys):
        mock_sys.platform = "freebsd"
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            get_capture_command("/tmp/out.mkv", 30, 0)

    @patch("neurascreen.platform.sys")
    def test_common_encoding_params(self, mock_sys):
        for platform in ["darwin", "linux", "win32"]:
            mock_sys.platform = platform
            cmd = get_capture_command("/tmp/out.mkv", 30, 0)
            assert "-c:v" in cmd
            assert "libx264" in cmd
            assert "ultrafast" in cmd
            assert "matroska" in cmd


class TestAudioPlayCommand:
    """Tests for get_audio_play_command()."""

    @patch("neurascreen.platform.sys")
    def test_macos_afplay(self, mock_sys):
        mock_sys.platform = "darwin"
        cmd = get_audio_play_command("/tmp/audio.wav")
        assert cmd == ["afplay", "/tmp/audio.wav"]

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_linux_paplay_preferred(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: "/usr/bin/paplay" if x == "paplay" else None
        cmd = get_audio_play_command("/tmp/audio.wav")
        assert cmd[0] == "paplay"

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_linux_aplay_fallback(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: "/usr/bin/aplay" if x == "aplay" else None
        cmd = get_audio_play_command("/tmp/audio.wav")
        assert cmd[0] == "aplay"
        assert "-q" in cmd

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_linux_no_player_raises(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: None
        with pytest.raises(RuntimeError, match="No audio player found"):
            get_audio_play_command("/tmp/audio.wav")

    @patch("neurascreen.platform.sys")
    def test_windows_powershell(self, mock_sys):
        mock_sys.platform = "win32"
        cmd = get_audio_play_command("/tmp/audio.wav")
        assert cmd[0] == "powershell"
        assert "SoundPlayer" in cmd[-1]

    @patch("neurascreen.platform.sys")
    def test_unsupported_platform_raises(self, mock_sys):
        mock_sys.platform = "freebsd"
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            get_audio_play_command("/tmp/audio.wav")


class TestDependencyChecks:
    """Tests for dependency checking functions."""

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_capture_deps_ok_macos(self, mock_sys, mock_shutil):
        mock_sys.platform = "darwin"
        mock_shutil.which = lambda x: "/usr/local/bin/ffmpeg" if x == "ffmpeg" else None
        assert check_capture_dependencies() == []

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_capture_deps_missing_ffmpeg(self, mock_sys, mock_shutil):
        mock_sys.platform = "darwin"
        mock_shutil.which = lambda x: None
        errors = check_capture_dependencies()
        assert len(errors) == 1
        assert "ffmpeg" in errors[0]

    @patch.dict("os.environ", {}, clear=True)
    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_capture_deps_linux_no_display(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: "/usr/bin/ffmpeg"
        errors = check_capture_dependencies()
        assert any("DISPLAY" in e for e in errors)

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_audio_deps_macos_ok(self, mock_sys, mock_shutil):
        mock_sys.platform = "darwin"
        mock_shutil.which = lambda x: "/usr/bin/afplay" if x == "afplay" else None
        assert check_audio_dependencies() == []

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_audio_deps_linux_paplay(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: "/usr/bin/paplay" if x == "paplay" else None
        assert check_audio_dependencies() == []

    @patch("neurascreen.platform.shutil")
    @patch("neurascreen.platform.sys")
    def test_audio_deps_linux_none(self, mock_sys, mock_shutil):
        mock_sys.platform = "linux"
        mock_shutil.which = lambda x: None
        errors = check_audio_dependencies()
        assert len(errors) == 1
