"""Tests for TTS GUI components — pure logic, no Qt dependency."""

import json
import tempfile
from pathlib import Path


class TestNarrationStats:
    """Test narration statistics computation."""

    def test_empty_steps(self):
        from neurascreen.gui.tts.stats import compute_stats
        stats = compute_stats([])
        assert stats.total_steps == 0
        assert stats.narrated_steps == 0
        assert stats.word_count == 0
        assert stats.estimated_reading_ms == 0

    def test_no_narration(self):
        from neurascreen.gui.tts.stats import compute_stats
        steps = [
            {"action": "navigate", "url": "/page"},
            {"action": "click", "selector": "button"},
        ]
        stats = compute_stats(steps)
        assert stats.total_steps == 2
        assert stats.narrated_steps == 0
        assert stats.word_count == 0

    def test_with_narration(self):
        from neurascreen.gui.tts.stats import compute_stats
        steps = [
            {"action": "wait", "narration": "Voici la page d'accueil", "duration": 3000},
            {"action": "click", "selector": "button"},
            {"action": "wait", "narration": "On clique sur le bouton", "wait": 2000},
        ]
        stats = compute_stats(steps)
        assert stats.total_steps == 3
        assert stats.narrated_steps == 2
        assert stats.word_count == 9  # 5 + 4 words
        assert stats.total_wait_ms == 5000  # 3000 + 2000

    def test_narrated_ratio(self):
        from neurascreen.gui.tts.stats import compute_stats
        steps = [
            {"action": "wait", "narration": "Hello"},
            {"action": "click"},
            {"action": "wait", "narration": "World"},
        ]
        stats = compute_stats(steps)
        assert stats.narrated_ratio == "2/3"

    def test_estimated_reading_time(self):
        from neurascreen.gui.tts.stats import compute_stats, WORDS_PER_MINUTE
        # 130 words should take exactly 1 minute
        words = " ".join(["word"] * WORDS_PER_MINUTE)
        steps = [{"action": "wait", "narration": words}]
        stats = compute_stats(steps)
        assert stats.estimated_reading_ms == 60000

    def test_format_duration_seconds(self):
        from neurascreen.gui.tts.stats import NarrationStats
        stats = NarrationStats(0, 0, 0, 0, 0)
        assert stats.format_duration(5000) == "5s"
        assert stats.format_duration(45000) == "45s"

    def test_format_duration_minutes(self):
        from neurascreen.gui.tts.stats import NarrationStats
        stats = NarrationStats(0, 0, 0, 0, 0)
        assert stats.format_duration(60000) == "1m 00s"
        assert stats.format_duration(90000) == "1m 30s"
        assert stats.format_duration(125000) == "2m 05s"

    def test_total_duration(self):
        from neurascreen.gui.tts.stats import compute_stats
        steps = [
            {"action": "wait", "narration": "Hello world", "duration": 2000},
            {"action": "click", "wait": 1000},
        ]
        stats = compute_stats(steps)
        assert stats.total_wait_ms == 3000
        assert stats.total_duration_s > 0


class TestPronunciation:
    """Test pronunciation substitution logic."""

    def test_load_builtins(self):
        from neurascreen.gui.tts.pronunciation import load_substitutions
        subs = load_substitutions(Path("/nonexistent/path.json"))
        assert len(subs) > 0
        assert any(s.word == "NeuraHub" for s in subs)
        assert any(s.word == "workflow" for s in subs)

    def test_save_and_load(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, save_substitutions, load_substitutions,
        )
        subs = [
            Substitution("test", "tesse", "French pronunciation"),
            Substitution("API", "A P I", "Spell out"),
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        save_substitutions(subs, path)
        loaded = load_substitutions(path)
        assert len(loaded) == 2
        assert loaded[0].word == "test"
        assert loaded[0].replacement == "tesse"
        assert loaded[1].word == "API"
        path.unlink()

    def test_save_creates_valid_json(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, save_substitutions,
        )
        subs = [Substitution("hello", "ello", "H muet")]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        save_substitutions(subs, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert data[0]["word"] == "hello"
        path.unlink()

    def test_find_matches(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, find_matches,
        )
        subs = [
            Substitution("NeuraHub", "Neura Hub", ""),
            Substitution("workflow", "worke flo", ""),
        ]
        text = "Voici le NeuraHub et son workflow principal"
        matches = find_matches(text, subs)
        assert len(matches) == 2
        assert matches[0][0] == "NeuraHub"
        assert matches[1][0] == "workflow"

    def test_find_matches_case_insensitive(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, find_matches,
        )
        subs = [Substitution("neurahub", "Neura Hub", "")]
        text = "Le NeuraHub est un module"
        matches = find_matches(text, subs)
        assert len(matches) == 1

    def test_find_matches_no_match(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, find_matches,
        )
        subs = [Substitution("NeuraHub", "Neura Hub", "")]
        text = "Pas de correspondance ici"
        matches = find_matches(text, subs)
        assert len(matches) == 0

    def test_apply_substitutions(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, apply_substitutions,
        )
        subs = [
            Substitution("NeuraHub", "Neura Hub", ""),
            Substitution("flux", "flu", ""),
        ]
        text = "Le NeuraHub gère les flux de données"
        result = apply_substitutions(text, subs)
        assert "Neura Hub" in result
        assert "flu " in result
        assert "NeuraHub" not in result

    def test_apply_preserves_unmatched(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, apply_substitutions,
        )
        subs = [Substitution("NeuraHub", "Neura Hub", "")]
        text = "Le dashboard principal"
        result = apply_substitutions(text, subs)
        assert result == text

    def test_empty_substitutions(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, find_matches, apply_substitutions,
        )
        text = "Hello world"
        assert find_matches(text, []) == []
        assert apply_substitutions(text, []) == text

    def test_empty_word_ignored(self):
        from neurascreen.gui.tts.pronunciation import (
            Substitution, find_matches, apply_substitutions,
        )
        subs = [Substitution("", "something", "")]
        text = "Hello world"
        assert find_matches(text, subs) == []
        assert apply_substitutions(text, subs) == text

    def test_load_invalid_json(self):
        from neurascreen.gui.tts.pronunciation import load_substitutions
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not json")
            path = Path(f.name)
        # Should fallback to builtins
        subs = load_substitutions(path)
        assert len(subs) > 0
        path.unlink()


class TestVoices:
    """Test voice configuration per provider."""

    def test_load_builtins(self):
        from neurascreen.gui.tts.voices import load_voices, PROVIDER_NAMES
        configs = load_voices(Path("/nonexistent/voices.json"))
        for name in PROVIDER_NAMES:
            assert name in configs

    def test_openai_has_preset_voices(self):
        from neurascreen.gui.tts.voices import load_voices
        configs = load_voices(Path("/nonexistent/voices.json"))
        openai = configs["openai"]
        voice_ids = [v.id for v in openai.voices]
        assert "alloy" in voice_ids
        assert "shimmer" in voice_ids
        assert len(openai.voices) >= 9

    def test_openai_has_models(self):
        from neurascreen.gui.tts.voices import load_voices
        configs = load_voices(Path("/nonexistent/voices.json"))
        assert "tts-1-hd" in configs["openai"].models

    def test_google_has_french_voices(self):
        from neurascreen.gui.tts.voices import load_voices
        configs = load_voices(Path("/nonexistent/voices.json"))
        voice_ids = [v.id for v in configs["google"].voices]
        assert any("fr-FR" in vid for vid in voice_ids)

    def test_save_and_load(self):
        from neurascreen.gui.tts.voices import (
            load_voices, save_voices, add_voice,
        )
        configs = load_voices(Path("/nonexistent/voices.json"))
        add_voice(configs, "gradium", "test123", "Test Voice")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        save_voices(configs, path)
        reloaded = load_voices(path)
        gradium_ids = [v.id for v in reloaded["gradium"].voices]
        assert "test123" in gradium_ids
        path.unlink()

    def test_add_voice(self):
        from neurascreen.gui.tts.voices import load_voices, add_voice
        configs = load_voices(Path("/nonexistent/voices.json"))
        assert add_voice(configs, "gradium", "abc123", "My Voice") is True
        assert any(v.id == "abc123" for v in configs["gradium"].voices)

    def test_add_voice_duplicate(self):
        from neurascreen.gui.tts.voices import load_voices, add_voice
        configs = load_voices(Path("/nonexistent/voices.json"))
        add_voice(configs, "gradium", "abc123", "My Voice")
        assert add_voice(configs, "gradium", "abc123", "Same ID") is False

    def test_remove_voice(self):
        from neurascreen.gui.tts.voices import load_voices, add_voice, remove_voice
        configs = load_voices(Path("/nonexistent/voices.json"))
        add_voice(configs, "gradium", "to_remove", "Remove Me")
        assert remove_voice(configs, "gradium", "to_remove") is True
        assert not any(v.id == "to_remove" for v in configs["gradium"].voices)

    def test_remove_voice_not_found(self):
        from neurascreen.gui.tts.voices import load_voices, remove_voice
        configs = load_voices(Path("/nonexistent/voices.json"))
        assert remove_voice(configs, "gradium", "nonexistent") is False

    def test_add_voice_new_provider(self):
        from neurascreen.gui.tts.voices import load_voices, add_voice
        configs = load_voices(Path("/nonexistent/voices.json"))
        assert add_voice(configs, "custom_provider", "v1", "Voice 1") is True
        assert "custom_provider" in configs

    def test_get_provider_help(self):
        from neurascreen.gui.tts.voices import get_provider_help
        assert "gradium.ai" in get_provider_help("gradium")
        assert "elevenlabs.io" in get_provider_help("elevenlabs")
        assert "Enter" in get_provider_help("unknown_provider")

    def test_provider_defaults(self):
        from neurascreen.gui.tts.voices import load_voices
        configs = load_voices(Path("/nonexistent/voices.json"))
        assert configs["openai"].default_voice == "alloy"
        assert configs["openai"].default_model == "tts-1-hd"
        assert configs["coqui"].default_voice == "default"

    def test_load_invalid_json_falls_back(self):
        from neurascreen.gui.tts.voices import load_voices, PROVIDER_NAMES
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json")
            path = Path(f.name)
        configs = load_voices(path)
        for name in PROVIDER_NAMES:
            assert name in configs
        path.unlink()


class TestAudioPreview:
    """Test audio preview components (import only, no Qt instantiation)."""

    def test_import_audio_preview_manager(self):
        from neurascreen.gui.tts.audio_preview import AudioPreviewManager
        assert AudioPreviewManager is not None

    def test_import_tts_panel(self):
        from neurascreen.gui.tts.tts_panel import TTSPanel
        assert TTSPanel is not None
