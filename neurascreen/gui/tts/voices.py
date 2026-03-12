"""Voice configuration per provider — load/save ~/.neurascreen/voices.json.

Pure logic, no Qt dependency.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path

logger = logging.getLogger("neurascreen.gui")

VOICES_FILE = Path.home() / ".neurascreen" / "voices.json"


@dataclass
class Voice:
    """A single voice entry."""

    id: str
    name: str


@dataclass
class ProviderConfig:
    """Configuration for one TTS provider."""

    voices: list[Voice] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    default_voice: str = ""
    default_model: str = ""


# Built-in defaults per provider
BUILTIN_PROVIDERS: dict[str, ProviderConfig] = {
    "gradium": ProviderConfig(
        voices=[],
        models=["default"],
        default_voice="",
        default_model="default",
    ),
    "openai": ProviderConfig(
        voices=[
            Voice("alloy", "Alloy"),
            Voice("ash", "Ash"),
            Voice("coral", "Coral"),
            Voice("echo", "Echo"),
            Voice("fable", "Fable"),
            Voice("nova", "Nova"),
            Voice("onyx", "Onyx"),
            Voice("sage", "Sage"),
            Voice("shimmer", "Shimmer"),
        ],
        models=["tts-1", "tts-1-hd", "gpt-4o-mini-tts"],
        default_voice="alloy",
        default_model="tts-1-hd",
    ),
    "elevenlabs": ProviderConfig(
        voices=[],
        models=["eleven_multilingual_v2", "eleven_monolingual_v1"],
        default_voice="",
        default_model="eleven_multilingual_v2",
    ),
    "google": ProviderConfig(
        voices=[
            Voice("fr-FR-Neural2-A", "Neural2 A (Female)"),
            Voice("fr-FR-Neural2-B", "Neural2 B (Male)"),
            Voice("fr-FR-Neural2-C", "Neural2 C (Female)"),
            Voice("fr-FR-Neural2-D", "Neural2 D (Male)"),
            Voice("fr-FR-Neural2-E", "Neural2 E (Female)"),
            Voice("fr-FR-Wavenet-A", "Wavenet A (Female)"),
            Voice("fr-FR-Wavenet-B", "Wavenet B (Male)"),
            Voice("fr-FR-Wavenet-C", "Wavenet C (Female)"),
            Voice("fr-FR-Wavenet-D", "Wavenet D (Male)"),
            Voice("fr-FR-Wavenet-E", "Wavenet E (Female)"),
        ],
        models=[],
        default_voice="fr-FR-Neural2-A",
        default_model="",
    ),
    "coqui": ProviderConfig(
        voices=[Voice("default", "Default")],
        models=[],
        default_voice="default",
        default_model="",
    ),
}

PROVIDER_NAMES = ["gradium", "openai", "elevenlabs", "google", "coqui"]


def _serialize(configs: dict[str, ProviderConfig]) -> dict:
    """Convert configs to JSON-serializable dict."""
    result = {}
    for name, cfg in configs.items():
        result[name] = {
            "voices": [asdict(v) for v in cfg.voices],
            "models": cfg.models,
            "default_voice": cfg.default_voice,
            "default_model": cfg.default_model,
        }
    return result


def _deserialize(data: dict) -> dict[str, ProviderConfig]:
    """Parse JSON dict into ProviderConfig objects."""
    result = {}
    for name, cfg_data in data.items():
        voices = [Voice(**v) for v in cfg_data.get("voices", [])]
        result[name] = ProviderConfig(
            voices=voices,
            models=cfg_data.get("models", []),
            default_voice=cfg_data.get("default_voice", ""),
            default_model=cfg_data.get("default_model", ""),
        )
    return result


def load_voices(path: Path | None = None) -> dict[str, ProviderConfig]:
    """Load voice configurations from JSON. Returns builtins if file doesn't exist."""
    target = path or VOICES_FILE

    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            configs = _deserialize(data)
            # Merge with builtins for any missing providers
            for name, builtin in BUILTIN_PROVIDERS.items():
                if name not in configs:
                    configs[name] = ProviderConfig(
                        voices=list(builtin.voices),
                        models=list(builtin.models),
                        default_voice=builtin.default_voice,
                        default_model=builtin.default_model,
                    )
            return configs
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning("Failed to load voices file %s: %s", target, e)

    # Return deep copy of builtins
    return {
        name: ProviderConfig(
            voices=list(cfg.voices),
            models=list(cfg.models),
            default_voice=cfg.default_voice,
            default_model=cfg.default_model,
        )
        for name, cfg in BUILTIN_PROVIDERS.items()
    }


def save_voices(configs: dict[str, ProviderConfig], path: Path | None = None) -> None:
    """Save voice configurations to JSON file."""
    target = path or VOICES_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    data = _serialize(configs)
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_voice(
    configs: dict[str, ProviderConfig],
    provider: str,
    voice_id: str,
    voice_name: str,
) -> bool:
    """Add a voice to a provider. Returns False if already exists."""
    cfg = configs.get(provider)
    if cfg is None:
        cfg = ProviderConfig()
        configs[provider] = cfg

    # Check duplicate
    for v in cfg.voices:
        if v.id == voice_id:
            return False

    cfg.voices.append(Voice(voice_id, voice_name))
    return True


def remove_voice(
    configs: dict[str, ProviderConfig],
    provider: str,
    voice_id: str,
) -> bool:
    """Remove a voice from a provider. Returns False if not found."""
    cfg = configs.get(provider)
    if cfg is None:
        return False

    for i, v in enumerate(cfg.voices):
        if v.id == voice_id:
            cfg.voices.pop(i)
            return True
    return False


def get_provider_help(provider: str) -> str:
    """Return help text for voice ID format per provider."""
    helps = {
        "gradium": "Copy voice ID from gradium.ai studio (e.g. b35yykvVppLXyw_l)",
        "openai": "Choose from preset voices or enter a custom voice name",
        "elevenlabs": "Copy voice ID from elevenlabs.io (e.g. 21m00Tcm4TlvDq8ikWAM)",
        "google": "Use format: fr-FR-{Type}-{Letter} (e.g. fr-FR-Neural2-A)",
        "coqui": "Enter speaker name or 'default' for the default speaker",
    }
    return helps.get(provider, "Enter voice identifier")
