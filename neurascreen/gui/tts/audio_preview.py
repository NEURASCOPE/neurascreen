"""Audio preview — generate and play TTS for a single step."""

import logging
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QObject

from ...config import Config
from ...tts import create_tts_client, get_wav_duration_ms, BaseTTSClient
from ...platform import get_audio_play_command

logger = logging.getLogger("neurascreen.gui")


class AudioGenerateWorker(QObject):
    """Worker that generates TTS audio in a background thread."""

    finished = Signal(int, str, int)  # (step_index, wav_path, duration_ms)
    error = Signal(int, str)  # (step_index, error_message)

    def __init__(self, tts_client: BaseTTSClient, step_index: int, text: str):
        super().__init__()
        self._tts = tts_client
        self._step_index = step_index
        self._text = text

    def run(self) -> None:
        try:
            wav_path = self._tts.generate_audio(self._text)
            duration = get_wav_duration_ms(wav_path)
            self.finished.emit(self._step_index, str(wav_path), duration)
        except Exception as e:
            logger.error("TTS generation failed for step %d: %s", self._step_index, e)
            self.error.emit(self._step_index, str(e))


class AudioPreviewManager(QObject):
    """Manages TTS generation and playback for step previews."""

    preview_started = Signal(int)  # step_index
    preview_ready = Signal(int, int)  # (step_index, duration_ms)
    preview_error = Signal(int, str)  # (step_index, error_message)
    preview_playing = Signal(int)  # step_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tts_client: BaseTTSClient | None = None
        self._thread: QThread | None = None
        self._worker: AudioGenerateWorker | None = None
        self._play_process: subprocess.Popen | None = None
        self._cache_info: dict[int, tuple[str, int]] = {}  # step_index -> (path, duration_ms)

    def configure(self, config: Config) -> None:
        """Create/update the TTS client from config."""
        try:
            self._tts_client = create_tts_client(config)
            logger.info("TTS client configured: %s", config.tts_provider)
        except Exception as e:
            logger.error("Failed to create TTS client: %s", e)
            self._tts_client = None

    def is_configured(self) -> bool:
        return self._tts_client is not None

    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def preview_step(self, step_index: int, text: str) -> None:
        """Generate and play audio for a step."""
        if not self._tts_client:
            self.preview_error.emit(step_index, "TTS not configured")
            return

        if self.is_busy():
            self.preview_error.emit(step_index, "Already generating audio")
            return

        if not text.strip():
            self.preview_error.emit(step_index, "No narration text")
            return

        # Check cache
        cache_path = self._tts_client._cache_path(text)
        if cache_path.exists():
            duration = get_wav_duration_ms(cache_path)
            self._cache_info[step_index] = (str(cache_path), duration)
            self.preview_ready.emit(step_index, duration)
            self._play_wav(str(cache_path))
            self.preview_playing.emit(step_index)
            return

        # Generate in background
        self.preview_started.emit(step_index)
        self._thread = QThread()
        self._worker = AudioGenerateWorker(self._tts_client, step_index, text)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generated)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_generated(self, step_index: int, wav_path: str, duration_ms: int) -> None:
        self._cache_info[step_index] = (wav_path, duration_ms)
        self.preview_ready.emit(step_index, duration_ms)
        self._play_wav(wav_path)
        self.preview_playing.emit(step_index)
        self._cleanup_thread()

    def _on_error(self, step_index: int, error_msg: str) -> None:
        self.preview_error.emit(step_index, error_msg)
        self._cleanup_thread()

    def _play_wav(self, wav_path: str) -> None:
        """Play a WAV file using the platform's audio command."""
        self.stop_playback()
        try:
            cmd = get_audio_play_command(wav_path)
            self._play_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error("Failed to play audio: %s", e)

    def stop_playback(self) -> None:
        """Stop any currently playing audio."""
        if self._play_process and self._play_process.poll() is None:
            self._play_process.terminate()
            self._play_process = None

    def get_cached_duration(self, step_index: int) -> int | None:
        """Return cached duration for a step, or None if not cached."""
        info = self._cache_info.get(step_index)
        return info[1] if info else None

    def is_cached(self, text: str) -> bool:
        """Check if audio for this text is in the TTS cache."""
        if not self._tts_client:
            return False
        return self._tts_client._cache_path(text).exists()

    def _cleanup_thread(self) -> None:
        self._thread = None
        self._worker = None

    def test_connection(self, text: str = "Test de connexion audio.") -> None:
        """Test TTS connection by generating a short sample."""
        self.preview_step(-1, text)
