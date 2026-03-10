"""TTS abstraction layer supporting multiple providers."""

import hashlib
import logging
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from .config import Config

logger = logging.getLogger("videogen")


class BaseTTSClient(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.temp_dir / "audio_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str) -> Path:
        """Get cache file path for a given text."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{text_hash}.wav"

    def generate_audio(self, text: str, output_path: Path | None = None) -> Path:
        """Generate a WAV audio file from text. Uses cache when possible."""
        if not text.strip():
            raise ValueError("Cannot generate audio from empty text")

        cache_path = self._cache_path(text)
        if cache_path.exists() and output_path is None:
            logger.debug(f"  Audio cache hit: {cache_path.name}")
            return cache_path

        target_path = output_path or cache_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"  Generating audio ({len(text)} chars): {text[:60]}...")

        audio_bytes = self._synthesize(text)

        target_path.write_bytes(audio_bytes)
        logger.info(f"  Audio saved: {target_path.name} ({target_path.stat().st_size / 1024:.1f} KB)")

        if output_path and not cache_path.exists():
            cache_path.write_bytes(audio_bytes)

        return target_path

    @abstractmethod
    def _synthesize(self, text: str) -> bytes:
        """Synthesize text to WAV audio bytes. Must be implemented by subclasses."""
        ...

    def generate_all(self, narrations: list[tuple[int, str]]) -> dict[int, Path]:
        """Generate audio for all narration texts."""
        results = {}
        total_chars = 0

        for step_idx, text in narrations:
            if not text.strip():
                continue
            path = self.generate_audio(text)
            results[step_idx] = path
            total_chars += len(text)

        logger.info(f"Generated {len(results)} audio files ({total_chars} chars)")
        return results


class GradiumTTSClient(BaseTTSClient):
    """Gradium TTS provider."""

    def _synthesize(self, text: str) -> bytes:
        import asyncio
        from gradium import GradiumClient, TTSSetup

        client = GradiumClient(api_key=self.config.tts_api_key)
        setup = TTSSetup(
            model_name=self.config.tts_model or "default",
            output_format="wav",
        )
        if self.config.tts_voice_id:
            setup["voice_id"] = self.config.tts_voice_id

        result = asyncio.run(client.tts(setup=setup, text=text))
        return result.raw_data


class ElevenLabsTTSClient(BaseTTSClient):
    """ElevenLabs TTS provider."""

    def _synthesize(self, text: str) -> bytes:
        import requests

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.config.tts_voice_id}"
        headers = {
            "xi-api-key": self.config.tts_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        }
        payload = {
            "text": text,
            "model_id": self.config.tts_model or "eleven_multilingual_v2",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.content


class CoquiTTSClient(BaseTTSClient):
    """Coqui TTS provider (local or API)."""

    def _synthesize(self, text: str) -> bytes:
        import requests

        url = self.config.tts_api_key  # For Coqui, API key is the server URL
        if not url.startswith("http"):
            url = f"http://{url}"

        response = requests.post(
            f"{url}/api/tts",
            json={"text": text, "speaker_id": self.config.tts_voice_id or "default"},
            timeout=60,
        )
        response.raise_for_status()
        return response.content


class OpenAITTSClient(BaseTTSClient):
    """OpenAI TTS provider (tts-1 / tts-1-hd)."""

    def _synthesize(self, text: str) -> bytes:
        import requests

        headers = {
            "Authorization": f"Bearer {self.config.tts_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.tts_model or "tts-1-hd",
            "input": text,
            "voice": self.config.tts_voice_id or "alloy",
            "response_format": "wav",
        }

        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            json=payload, headers=headers, timeout=60,
        )
        response.raise_for_status()
        return response.content


class GoogleTTSClient(BaseTTSClient):
    """Google Cloud Text-to-Speech provider."""

    def _synthesize(self, text: str) -> bytes:
        import requests

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.config.tts_api_key,
        }
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "fr-FR",
                "name": self.config.tts_voice_id or "fr-FR-Neural2-A",
            },
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000},
        }

        response = requests.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            json=payload, headers=headers, timeout=60,
        )
        response.raise_for_status()

        import base64
        audio_content = response.json()["audioContent"]
        return base64.b64decode(audio_content)


def create_tts_client(config: Config) -> BaseTTSClient:
    """Factory function to create the appropriate TTS client."""
    provider = config.tts_provider.lower()

    match provider:
        case "gradium":
            return GradiumTTSClient(config)
        case "elevenlabs" | "eleven_labs":
            return ElevenLabsTTSClient(config)
        case "coqui":
            return CoquiTTSClient(config)
        case "openai":
            return OpenAITTSClient(config)
        case "google" | "google_cloud":
            return GoogleTTSClient(config)
        case _:
            raise ValueError(
                f"Unknown TTS provider: '{provider}'. "
                f"Supported: gradium, elevenlabs, coqui, openai, google"
            )


def get_wav_duration_ms(wav_path: Path) -> int:
    """Get duration of a WAV file in milliseconds.

    Some TTS providers produce WAV files with incorrect nframes headers,
    so we calculate duration from actual file size.
    """
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        if rate == 0 or channels == 0 or sampwidth == 0:
            return 0
        data_size = wav_path.stat().st_size - 44
        bytes_per_second = rate * channels * sampwidth
        duration_s = data_size / bytes_per_second
        return int(duration_s * 1000)
