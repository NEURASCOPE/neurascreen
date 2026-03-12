"""Platform detection and OS-specific command builders for screen capture and audio playback."""

import shutil
import sys

PLATFORM_MACOS = "darwin"
PLATFORM_LINUX = "linux"
PLATFORM_WINDOWS = "win32"


def get_platform() -> str:
    """Return the current platform identifier."""
    return sys.platform


def is_macos() -> bool:
    return sys.platform == PLATFORM_MACOS


def is_linux() -> bool:
    return sys.platform.startswith(PLATFORM_LINUX)


def is_windows() -> bool:
    return sys.platform == PLATFORM_WINDOWS


def get_capture_command(
    output_path: str,
    fps: int,
    capture_screen: int | str,
    capture_display: str = "",
) -> list[str]:
    """Build the ffmpeg screen capture command for the current platform.

    Args:
        output_path: Path for the output MKV file.
        fps: Frames per second.
        capture_screen: Screen index (macOS avfoundation) or ignored on other platforms.
        capture_display: Display identifier — X11 display for Linux (e.g. ":0.0+0,0"),
                         or window title for Windows (e.g. "desktop"). Falls back to
                         sensible defaults per platform if empty.

    Returns:
        Complete ffmpeg command as a list of strings.
    """
    base = ["ffmpeg", "-y"]
    encode = [
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "15",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-f", "matroska",
        output_path,
    ]

    if is_macos():
        return base + [
            "-f", "avfoundation",
            "-framerate", str(fps),
            "-capture_cursor", "1",
            "-i", f"{capture_screen}:none",
        ] + encode

    if is_linux():
        display = capture_display or ":0.0"
        return base + [
            "-f", "x11grab",
            "-framerate", str(fps),
            "-draw_mouse", "1",
            "-i", display,
        ] + encode

    if is_windows():
        input_name = capture_display or "desktop"
        return base + [
            "-f", "gdigrab",
            "-framerate", str(fps),
            "-draw_mouse", "1",
            "-i", input_name,
        ] + encode

    raise RuntimeError(f"Unsupported platform for screen capture: {sys.platform}")


def get_audio_play_command(audio_path: str) -> list[str]:
    """Return the command to play a WAV file on the current platform.

    Args:
        audio_path: Path to the WAV file.

    Returns:
        Command as a list of strings.
    """
    if is_macos():
        return ["afplay", str(audio_path)]

    if is_linux():
        # Prefer paplay (PulseAudio) if available, fallback to aplay (ALSA)
        if shutil.which("paplay"):
            return ["paplay", str(audio_path)]
        if shutil.which("aplay"):
            return ["aplay", "-q", str(audio_path)]
        raise RuntimeError(
            "No audio player found. Install pulseaudio (paplay) or alsa-utils (aplay)."
        )

    if is_windows():
        # PowerShell can play WAV files natively via SoundPlayer
        return [
            "powershell", "-NoProfile", "-Command",
            f"(New-Object System.Media.SoundPlayer '{audio_path}').PlaySync()",
        ]

    raise RuntimeError(f"Unsupported platform for audio playback: {sys.platform}")


def get_platform_name() -> str:
    """Return a human-readable platform name."""
    if is_macos():
        return "macOS"
    if is_linux():
        return "Linux"
    if is_windows():
        return "Windows"
    return f"Unknown ({sys.platform})"


def check_capture_dependencies() -> list[str]:
    """Check that platform-specific capture dependencies are available.

    Returns:
        List of error messages (empty if all OK).
    """
    errors = []

    if not shutil.which("ffmpeg"):
        errors.append("ffmpeg not found. Install it for screen capture.")

    if is_linux():
        # x11grab requires an X11 display
        import os
        if not os.environ.get("DISPLAY"):
            errors.append("DISPLAY environment variable not set. x11grab requires X11.")

    return errors


def check_audio_dependencies() -> list[str]:
    """Check that platform-specific audio playback dependencies are available.

    Returns:
        List of error messages (empty if all OK).
    """
    errors = []

    if is_macos():
        if not shutil.which("afplay"):
            errors.append("afplay not found (should be built-in on macOS).")

    elif is_linux():
        if not shutil.which("paplay") and not shutil.which("aplay"):
            errors.append(
                "No audio player found. Install pulseaudio (paplay) or alsa-utils (aplay)."
            )

    elif is_windows():
        if not shutil.which("powershell"):
            errors.append("PowerShell not found (required for audio playback on Windows).")

    return errors
