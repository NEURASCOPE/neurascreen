"""Configuration loader from .env file."""

import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment."""

    # Target application
    app_url: str
    app_email: str
    app_password: str
    login_url: str

    # Directories
    output_dir: Path
    temp_dir: Path
    logs_dir: Path
    scenarios_dir: Path

    # Browser
    browser_headless: bool
    video_width: int
    video_height: int
    video_fps: int

    # Screen capture (macOS)
    capture_screen: int
    browser_screen_offset: int

    # TTS
    tts_provider: str
    tts_api_key: str
    tts_voice_id: str
    tts_model: str

    @classmethod
    def load(cls, env_path: str | None = None) -> "Config":
        """Load configuration from .env file."""
        project_root = Path(__file__).parent.parent

        if env_path:
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(project_root / ".env", override=True)

        config = cls(
            # Target application
            app_url=os.getenv("APP_URL", "http://localhost:3000").rstrip("/"),
            app_email=os.getenv("APP_EMAIL", ""),
            app_password=os.getenv("APP_PASSWORD", ""),
            login_url=os.getenv("LOGIN_URL", "/login"),
            # Directories
            output_dir=Path(os.getenv("OUTPUT_DIR", str(project_root / "output"))),
            temp_dir=Path(os.getenv("TEMP_DIR", str(project_root / "temp"))),
            logs_dir=Path(os.getenv("LOGS_DIR", str(project_root / "logs"))),
            scenarios_dir=Path(os.getenv("SCENARIOS_DIR", str(project_root / "examples"))),
            # Browser
            browser_headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            video_width=int(os.getenv("VIDEO_WIDTH", "1920")),
            video_height=int(os.getenv("VIDEO_HEIGHT", "1080")),
            video_fps=int(os.getenv("VIDEO_FPS", "30")),
            # Screen capture
            capture_screen=int(os.getenv("CAPTURE_SCREEN", "0")),
            browser_screen_offset=int(os.getenv("BROWSER_SCREEN_OFFSET", "0")),
            # TTS
            tts_provider=os.getenv("TTS_PROVIDER", "gradium"),
            tts_api_key=os.getenv("TTS_API_KEY", ""),
            tts_voice_id=os.getenv("TTS_VOICE_ID", ""),
            tts_model=os.getenv("TTS_MODEL", "default"),
        )

        # Ensure directories exist
        config.output_dir.mkdir(parents=True, exist_ok=True)
        config.temp_dir.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        config.scenarios_dir.mkdir(parents=True, exist_ok=True)

        return config

    def validate(self) -> list[str]:
        """Validate required configuration. Returns list of errors."""
        errors = []
        if not self.app_url:
            errors.append("APP_URL is required")
        return errors

    def validate_tts(self) -> list[str]:
        """Validate TTS configuration."""
        errors = self.validate()
        if not self.tts_api_key:
            errors.append("TTS_API_KEY is required for narration")
        if not self.tts_provider:
            errors.append("TTS_PROVIDER is required (gradium, elevenlabs, coqui)")
        return errors
