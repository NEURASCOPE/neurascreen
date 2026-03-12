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

    # Screen capture
    capture_screen: int
    capture_display: str
    browser_screen_offset: int

    # TTS
    tts_provider: str
    tts_api_key: str
    tts_voice_id: str
    tts_model: str

    # Login form selectors
    login_email_selector: str
    login_password_selector: str
    login_submit_selector: str

    # Canvas selectors (for drag, delete_node, close_modal, zoom_out, fit_view)
    selector_draggable: str
    selector_canvas: str
    selector_delete_button: str
    selector_close_modal: str
    selector_zoom_out: str
    selector_fit_view: str

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
            capture_display=os.getenv("CAPTURE_DISPLAY", ""),
            browser_screen_offset=int(os.getenv("BROWSER_SCREEN_OFFSET", "0")),
            # TTS
            tts_provider=os.getenv("TTS_PROVIDER", "gradium"),
            tts_api_key=os.getenv("TTS_API_KEY", ""),
            tts_voice_id=os.getenv("TTS_VOICE_ID", ""),
            tts_model=os.getenv("TTS_MODEL", "default"),
            # Login form selectors
            login_email_selector=os.getenv(
                "LOGIN_EMAIL_SELECTOR", "input[name='email'], input[type='email']"
            ),
            login_password_selector=os.getenv(
                "LOGIN_PASSWORD_SELECTOR", "input[name='password'], input[type='password']"
            ),
            login_submit_selector=os.getenv(
                "LOGIN_SUBMIT_SELECTOR", "button[type='submit']"
            ),
            # Canvas selectors
            selector_draggable=os.getenv("SELECTOR_DRAGGABLE", "[draggable='true']"),
            selector_canvas=os.getenv("SELECTOR_CANVAS", ".react-flow"),
            selector_delete_button=os.getenv(
                "SELECTOR_DELETE_BUTTON",
                'button[title="Delete"], button[title="Supprimer"]',
            ),
            selector_close_modal=os.getenv(
                "SELECTOR_CLOSE_MODAL",
                'div.fixed.inset-0 button:has-text("Cancel"), '
                'div.fixed.inset-0 button:has-text("Annuler"), '
                '[role="dialog"] button:has-text("Cancel"), '
                '[role="dialog"] button:has-text("Close")',
            ),
            selector_zoom_out=os.getenv(
                "SELECTOR_ZOOM_OUT", 'button[title="zoom out"]'
            ),
            selector_fit_view=os.getenv(
                "SELECTOR_FIT_VIEW", 'button[title="fit view"]'
            ),
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
