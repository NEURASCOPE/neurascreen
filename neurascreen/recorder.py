"""Video recording orchestrator using native screen capture via ffmpeg."""

import logging
import signal
import subprocess
import time
from pathlib import Path

from .config import Config
from .scenario import Scenario
from .browser import BrowserEngine
from .platform import get_capture_command, get_platform_name

logger = logging.getLogger("videogen")

CAPTURE_STABILIZE_DELAY = 2


class Recorder:
    """Orchestrates browser execution with native screen capture."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = BrowserEngine(config)
        self._ffmpeg_process: subprocess.Popen | None = None

    def _start_screen_capture(self, output_path: Path) -> None:
        """Start ffmpeg screen capture in background (platform-aware)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = get_capture_command(
            output_path=str(output_path),
            fps=self.config.video_fps,
            capture_screen=self.config.capture_screen,
            capture_display=self.config.capture_display,
        )

        logger.info(f"Starting screen capture on {get_platform_name()} (screen {self.config.capture_screen})...")
        self._ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        time.sleep(CAPTURE_STABILIZE_DELAY)

        if self._ffmpeg_process.poll() is not None:
            stderr = self._ffmpeg_process.stderr.read().decode() if self._ffmpeg_process.stderr else ""
            raise RuntimeError(f"Screen capture failed to start:\n{stderr[-500:]}")

        logger.info("Screen capture running")

    def _stop_screen_capture(self) -> None:
        """Stop ffmpeg screen capture gracefully."""
        if not self._ffmpeg_process:
            return

        logger.info("Stopping screen capture...")
        try:
            if self._ffmpeg_process.stdin:
                try:
                    self._ffmpeg_process.stdin.write(b"q\n")
                    self._ffmpeg_process.stdin.flush()
                    self._ffmpeg_process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass
            try:
                self._ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ffmpeg_process.send_signal(signal.SIGINT)
                try:
                    self._ffmpeg_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._ffmpeg_process.terminate()
                    try:
                        self._ffmpeg_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._ffmpeg_process.kill()
                        self._ffmpeg_process.wait()
        except Exception as e:
            logger.warning(f"Error stopping ffmpeg: {e}")
            self._ffmpeg_process.kill()
            self._ffmpeg_process.wait()

        returncode = self._ffmpeg_process.returncode
        logger.info(f"Screen capture stopped (exit code {returncode})")
        self._ffmpeg_process = None

    def record(
        self, scenario: Scenario, audio_map: dict[int, Path] | None = None
    ) -> tuple[Path, list[tuple[float, Path]]]:
        """Record a scenario execution via screen capture.

        Returns:
            Tuple of (raw_video_path, audio_timestamps).
        """
        logger.info(f"Starting recording: {scenario.title}")

        raw_video = self.config.temp_dir / "video" / "screen_capture.mkv"
        raw_video.parent.mkdir(parents=True, exist_ok=True)

        if audio_map:
            self.engine.audio_map = audio_map

        try:
            self.engine.start()
            self.engine.login()

            self._start_screen_capture(raw_video)

            self.engine._recording_start_time = time.time()
            self.engine.audio_timestamps = []

            self.engine.execute_scenario(scenario)
            time.sleep(1)
        finally:
            self._stop_screen_capture()
            self.engine.stop()

        if raw_video.exists():
            size_mb = raw_video.stat().st_size / (1024 * 1024)
            logger.info(f"Raw video captured: {raw_video} ({size_mb:.1f} MB)")
        else:
            raise RuntimeError("No video file produced by screen capture")

        audio_timestamps = self.engine.audio_timestamps
        logger.info(f"Audio timestamps recorded: {len(audio_timestamps)} segments")
        return raw_video, audio_timestamps

    def preview(self, scenario: Scenario) -> None:
        """Execute scenario without recording (for testing)."""
        logger.info(f"Preview mode: {scenario.title}")
        try:
            self.engine.start()
            self.engine.login()
            self.engine.execute_scenario(scenario)
        finally:
            self.engine.stop()
