"""Field definitions for the configuration manager.

Each field maps to a .env variable. Grouped by tab for the UI.
Pure data — no Qt dependency, fully testable.
"""

from dataclasses import dataclass, field
from pathlib import Path


# Field types
TYPE_URL = "url"
TYPE_TEXT = "text"
TYPE_PASSWORD = "password"
TYPE_BOOL = "bool"
TYPE_INT = "int"
TYPE_PATH = "path"
TYPE_COMBO = "combo"
TYPE_SELECTOR = "selector"

# Tab names (display order)
TAB_APPLICATION = "Application"
TAB_BROWSER = "Browser"
TAB_SCREEN_CAPTURE = "Screen Capture"
TAB_TTS = "TTS"
TAB_LOGIN_SELECTORS = "Login Selectors"
TAB_CANVAS_SELECTORS = "Canvas Selectors"
TAB_DIRECTORIES = "Directories"

TABS_ORDER = [
    TAB_APPLICATION,
    TAB_BROWSER,
    TAB_SCREEN_CAPTURE,
    TAB_TTS,
    TAB_LOGIN_SELECTORS,
    TAB_CANVAS_SELECTORS,
    TAB_DIRECTORIES,
]


@dataclass(frozen=True)
class FieldDef:
    """Definition of a single configuration field."""

    env_key: str
    label: str
    field_type: str
    default: str
    tooltip: str
    tab: str
    required: bool = False
    options: list[str] = field(default_factory=list)
    min_value: int = 0
    max_value: int = 99999


# All field definitions
FIELDS: list[FieldDef] = [
    # -- Application --
    FieldDef(
        env_key="APP_URL",
        label="Application URL",
        field_type=TYPE_URL,
        default="http://localhost:3000",
        tooltip="Base URL of the web application to record",
        tab=TAB_APPLICATION,
        required=True,
    ),
    FieldDef(
        env_key="APP_EMAIL",
        label="Email",
        field_type=TYPE_TEXT,
        default="",
        tooltip="Login credentials (leave empty to skip login)",
        tab=TAB_APPLICATION,
    ),
    FieldDef(
        env_key="APP_PASSWORD",
        label="Password",
        field_type=TYPE_PASSWORD,
        default="",
        tooltip="Login password",
        tab=TAB_APPLICATION,
    ),
    FieldDef(
        env_key="LOGIN_URL",
        label="Login path",
        field_type=TYPE_TEXT,
        default="/login",
        tooltip="Login page path (relative to APP_URL)",
        tab=TAB_APPLICATION,
    ),
    # -- Browser --
    FieldDef(
        env_key="BROWSER_HEADLESS",
        label="Headless mode",
        field_type=TYPE_BOOL,
        default="false",
        tooltip="Run browser in headless mode (true for CI, false for recording)",
        tab=TAB_BROWSER,
    ),
    FieldDef(
        env_key="VIDEO_WIDTH",
        label="Video width",
        field_type=TYPE_INT,
        default="1920",
        tooltip="Output video width in pixels",
        tab=TAB_BROWSER,
        min_value=640,
        max_value=7680,
    ),
    FieldDef(
        env_key="VIDEO_HEIGHT",
        label="Video height",
        field_type=TYPE_INT,
        default="1080",
        tooltip="Output video height in pixels",
        tab=TAB_BROWSER,
        min_value=480,
        max_value=4320,
    ),
    FieldDef(
        env_key="VIDEO_FPS",
        label="FPS",
        field_type=TYPE_INT,
        default="30",
        tooltip="Video frames per second",
        tab=TAB_BROWSER,
        min_value=15,
        max_value=120,
    ),
    # -- Screen Capture --
    FieldDef(
        env_key="CAPTURE_SCREEN",
        label="Screen index",
        field_type=TYPE_INT,
        default="0",
        tooltip="macOS: ffmpeg avfoundation screen index.\nFind yours: ffmpeg -f avfoundation -list_devices true -i \"\"",
        tab=TAB_SCREEN_CAPTURE,
        min_value=0,
        max_value=10,
    ),
    FieldDef(
        env_key="CAPTURE_DISPLAY",
        label="Display (Linux/Win)",
        field_type=TYPE_TEXT,
        default="",
        tooltip="Linux (x11grab): e.g. :0.0\nWindows (gdigrab): desktop or title=Window Name\nmacOS: not used",
        tab=TAB_SCREEN_CAPTURE,
    ),
    FieldDef(
        env_key="BROWSER_SCREEN_OFFSET",
        label="Screen X offset",
        field_type=TYPE_INT,
        default="0",
        tooltip="Pixel offset to position browser on the target screen via CDP.\nEach 2560px screen adds 2560.",
        tab=TAB_SCREEN_CAPTURE,
        min_value=0,
        max_value=30720,
    ),
    # -- TTS --
    FieldDef(
        env_key="TTS_PROVIDER",
        label="Provider",
        field_type=TYPE_COMBO,
        default="gradium",
        tooltip="TTS provider for narration",
        tab=TAB_TTS,
        options=["gradium", "elevenlabs", "openai", "google", "coqui"],
    ),
    FieldDef(
        env_key="TTS_API_KEY",
        label="API Key",
        field_type=TYPE_PASSWORD,
        default="",
        tooltip="API key for the chosen TTS provider",
        tab=TAB_TTS,
    ),
    FieldDef(
        env_key="TTS_VOICE_ID",
        label="Voice ID",
        field_type=TYPE_TEXT,
        default="",
        tooltip="Voice identifier (provider-specific).\nGradium: b35yykvVppLXyw_l\nElevenLabs: 21m00Tcm4TlvDq8ikWAM\nOpenAI: alloy|echo|fable|onyx|nova|shimmer",
        tab=TAB_TTS,
    ),
    FieldDef(
        env_key="TTS_MODEL",
        label="Model",
        field_type=TYPE_TEXT,
        default="default",
        tooltip="TTS model (provider-specific, optional).\nOpenAI: tts-1|tts-1-hd\nElevenLabs: eleven_multilingual_v2",
        tab=TAB_TTS,
    ),
    # -- Login Selectors --
    FieldDef(
        env_key="LOGIN_EMAIL_SELECTOR",
        label="Email selector",
        field_type=TYPE_SELECTOR,
        default="input[name='email'], input[type='email']",
        tooltip="CSS selector for the email input on the login page",
        tab=TAB_LOGIN_SELECTORS,
    ),
    FieldDef(
        env_key="LOGIN_PASSWORD_SELECTOR",
        label="Password selector",
        field_type=TYPE_SELECTOR,
        default="input[name='password'], input[type='password']",
        tooltip="CSS selector for the password input on the login page",
        tab=TAB_LOGIN_SELECTORS,
    ),
    FieldDef(
        env_key="LOGIN_SUBMIT_SELECTOR",
        label="Submit selector",
        field_type=TYPE_SELECTOR,
        default="button[type='submit']",
        tooltip="CSS selector for the submit button on the login page",
        tab=TAB_LOGIN_SELECTORS,
    ),
    # -- Canvas Selectors --
    FieldDef(
        env_key="SELECTOR_DRAGGABLE",
        label="Draggable",
        field_type=TYPE_SELECTOR,
        default="[draggable='true']",
        tooltip="CSS selector for draggable items in the palette",
        tab=TAB_CANVAS_SELECTORS,
    ),
    FieldDef(
        env_key="SELECTOR_CANVAS",
        label="Canvas",
        field_type=TYPE_SELECTOR,
        default=".react-flow",
        tooltip="CSS selector for the canvas drop target",
        tab=TAB_CANVAS_SELECTORS,
    ),
    FieldDef(
        env_key="SELECTOR_DELETE_BUTTON",
        label="Delete button",
        field_type=TYPE_SELECTOR,
        default='button[title="Delete"], button[title="Supprimer"]',
        tooltip="CSS selector for the delete button on canvas nodes",
        tab=TAB_CANVAS_SELECTORS,
    ),
    FieldDef(
        env_key="SELECTOR_CLOSE_MODAL",
        label="Close modal",
        field_type=TYPE_SELECTOR,
        default=(
            'div.fixed.inset-0 button:has-text("Cancel"), '
            'div.fixed.inset-0 button:has-text("Annuler"), '
            '[role="dialog"] button:has-text("Cancel"), '
            '[role="dialog"] button:has-text("Close")'
        ),
        tooltip="CSS selector for the close/cancel button in modals",
        tab=TAB_CANVAS_SELECTORS,
    ),
    FieldDef(
        env_key="SELECTOR_ZOOM_OUT",
        label="Zoom out",
        field_type=TYPE_SELECTOR,
        default='button[title="zoom out"]',
        tooltip="CSS selector for the zoom out button",
        tab=TAB_CANVAS_SELECTORS,
    ),
    FieldDef(
        env_key="SELECTOR_FIT_VIEW",
        label="Fit view",
        field_type=TYPE_SELECTOR,
        default='button[title="fit view"]',
        tooltip="CSS selector for the fit view button",
        tab=TAB_CANVAS_SELECTORS,
    ),
    # -- Directories --
    FieldDef(
        env_key="OUTPUT_DIR",
        label="Output",
        field_type=TYPE_PATH,
        default="./output",
        tooltip="Directory for generated videos",
        tab=TAB_DIRECTORIES,
    ),
    FieldDef(
        env_key="TEMP_DIR",
        label="Temp",
        field_type=TYPE_PATH,
        default="./temp",
        tooltip="Temporary files directory",
        tab=TAB_DIRECTORIES,
    ),
    FieldDef(
        env_key="LOGS_DIR",
        label="Logs",
        field_type=TYPE_PATH,
        default="./logs",
        tooltip="Logs directory",
        tab=TAB_DIRECTORIES,
    ),
    FieldDef(
        env_key="SCENARIOS_DIR",
        label="Scenarios",
        field_type=TYPE_PATH,
        default="./examples",
        tooltip="Default scenarios directory",
        tab=TAB_DIRECTORIES,
    ),
]


def get_fields_by_tab() -> dict[str, list[FieldDef]]:
    """Return fields grouped by tab name, in display order."""
    result: dict[str, list[FieldDef]] = {}
    for tab in TABS_ORDER:
        result[tab] = [f for f in FIELDS if f.tab == tab]
    return result


def get_defaults() -> dict[str, str]:
    """Return {env_key: default_value} for all fields."""
    return {f.env_key: f.default for f in FIELDS}


def get_field(env_key: str) -> FieldDef | None:
    """Find a field definition by env key."""
    for f in FIELDS:
        if f.env_key == env_key:
            return f
    return None


def validate_values(values: dict[str, str]) -> list[str]:
    """Validate a dict of {env_key: value}. Returns list of error strings."""
    errors = []
    for f in FIELDS:
        val = values.get(f.env_key, f.default)

        if f.required and not val.strip():
            errors.append(f"{f.label} is required")
            continue

        if f.field_type == TYPE_URL and val.strip():
            if not val.startswith(("http://", "https://")):
                errors.append(f"{f.label}: must start with http:// or https://")

        if f.field_type == TYPE_INT and val.strip():
            try:
                n = int(val)
                if n < f.min_value or n > f.max_value:
                    errors.append(f"{f.label}: must be between {f.min_value} and {f.max_value}")
            except ValueError:
                errors.append(f"{f.label}: must be a number")

        if f.field_type == TYPE_COMBO and val.strip() and f.options:
            if val not in f.options:
                errors.append(f"{f.label}: must be one of {', '.join(f.options)}")

    return errors


def parse_env_file(content: str) -> dict[str, str]:
    """Parse a .env file content into {key: value} dict.

    Preserves only key=value lines (ignores comments and blank lines).
    Handles quoted values.
    """
    result: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        # Remove surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def build_env_content(values: dict[str, str]) -> str:
    """Build .env file content from a values dict.

    Groups by tab with section headers. Only includes non-empty values
    and values that differ from defaults.
    """
    defaults = get_defaults()
    lines: list[str] = [
        "# =============================================================================",
        "# NeuraScreen — Configuration",
        "# =============================================================================",
        "# Generated by NeuraScreen Configuration Manager",
        "",
    ]

    for tab in TABS_ORDER:
        tab_fields = [f for f in FIELDS if f.tab == tab]
        section_lines: list[str] = []

        for f in tab_fields:
            val = values.get(f.env_key, "")
            # Always write required fields; skip empty non-required defaults
            if not val and not f.required:
                continue
            # Quote values containing spaces
            if " " in val or "," in val:
                val = f'"{val}"'
            section_lines.append(f"{f.env_key}={val}")

        if section_lines:
            lines.append(f"# --- {tab} ---")
            lines.extend(section_lines)
            lines.append("")

    return "\n".join(lines) + "\n"
