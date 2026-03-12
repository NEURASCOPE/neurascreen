"""Tests for advanced features (logic only, no Qt)."""

import json
import tempfile
from pathlib import Path


class TestScenarioStats:
    """Test scenario statistics computation."""

    def test_empty_steps(self):
        from neurascreen.gui.advanced.statistics import compute_scenario_stats
        stats = compute_scenario_stats([])
        assert stats.total_steps == 0
        assert stats.narrated_steps == 0
        assert stats.word_count == 0

    def test_basic_stats(self):
        from neurascreen.gui.advanced.statistics import compute_scenario_stats
        steps = [
            {"action": "navigate", "url": "/customer", "wait": 1500},
            {"action": "click", "selector": "#btn", "wait": 1000},
            {"action": "wait", "duration": 2000, "narration": "Hello world test"},
            {"action": "click_text", "text": "Save", "wait": 500},
        ]
        stats = compute_scenario_stats(steps)
        assert stats.total_steps == 4
        assert stats.narrated_steps == 1
        assert stats.silent_steps == 3
        assert stats.word_count == 3
        assert stats.action_counts["click"] == 1
        assert stats.action_counts["navigate"] == 1
        assert len(stats.unique_urls) == 1
        assert stats.unique_selectors == 1

    def test_multiple_urls(self):
        from neurascreen.gui.advanced.statistics import compute_scenario_stats
        steps = [
            {"action": "navigate", "url": "/a"},
            {"action": "navigate", "url": "/b"},
            {"action": "navigate", "url": "/a"},
        ]
        stats = compute_scenario_stats(steps)
        assert len(stats.unique_urls) == 2

    def test_format_duration(self):
        from neurascreen.gui.advanced.statistics import format_duration
        assert format_duration(0) == "0s"
        assert format_duration(5000) == "5s"
        assert format_duration(65000) == "1m 05s"
        assert format_duration(120000) == "2m 00s"

    def test_estimated_duration_includes_reading(self):
        from neurascreen.gui.advanced.statistics import compute_scenario_stats
        steps = [
            {"action": "wait", "duration": 1000, "narration": " ".join(["word"] * 130)},
        ]
        stats = compute_scenario_stats(steps)
        # 130 words at 130 wpm = 60s = 60000ms + 1000ms wait
        assert stats.estimated_duration_ms == 61000


class TestDiffSteps:
    """Test scenario diff engine."""

    def test_empty_lists(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps, diff_summary
        entries = diff_steps([], [])
        assert len(entries) == 0
        summary = diff_summary(entries)
        assert summary["unchanged"] == 0

    def test_identical(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps, diff_summary
        steps = [{"action": "click", "selector": "#a"}]
        entries = diff_steps(steps, steps)
        assert len(entries) == 1
        assert entries[0].kind == "unchanged"
        summary = diff_summary(entries)
        assert summary["unchanged"] == 1

    def test_added(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps
        a = [{"action": "click"}]
        b = [{"action": "click"}, {"action": "wait"}]
        entries = diff_steps(a, b)
        assert len(entries) == 2
        assert entries[0].kind == "unchanged"
        assert entries[1].kind == "added"

    def test_removed(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps
        a = [{"action": "click"}, {"action": "wait"}]
        b = [{"action": "click"}]
        entries = diff_steps(a, b)
        assert len(entries) == 2
        assert entries[1].kind == "removed"

    def test_modified(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps
        a = [{"action": "click", "selector": "#old"}]
        b = [{"action": "click", "selector": "#new"}]
        entries = diff_steps(a, b)
        assert len(entries) == 1
        assert entries[0].kind == "modified"
        assert "selector" in entries[0].changes

    def test_find_changes(self):
        from neurascreen.gui.advanced.diff_viewer import _find_changes
        a = {"action": "click", "selector": "#a", "wait": 1000}
        b = {"action": "click", "selector": "#b", "wait": 1000}
        changes = _find_changes(a, b)
        assert changes == ["selector"]

    def test_find_changes_added_field(self):
        from neurascreen.gui.advanced.diff_viewer import _find_changes
        a = {"action": "wait"}
        b = {"action": "wait", "narration": "hello"}
        changes = _find_changes(a, b)
        assert "narration" in changes

    def test_diff_summary(self):
        from neurascreen.gui.advanced.diff_viewer import diff_steps, diff_summary
        a = [{"action": "a"}, {"action": "b"}, {"action": "c"}]
        b = [{"action": "a"}, {"action": "B"}, {"action": "c"}, {"action": "d"}]
        entries = diff_steps(a, b)
        summary = diff_summary(entries)
        assert summary["unchanged"] == 2
        assert summary["modified"] == 1
        assert summary["added"] == 1


class TestAutosave:
    """Test autosave logic."""

    def test_save_and_load(self):
        from neurascreen.gui.advanced.autosave import (
            save_autosave, load_autosave, clear_autosave, autosave_path,
            AUTOSAVE_DIR,
        )
        import neurascreen.gui.advanced.autosave as mod

        # Use temp dir
        original_dir = mod.AUTOSAVE_DIR
        mod.AUTOSAVE_DIR = Path(tempfile.mkdtemp()) / "autosave"

        try:
            scenario = {"title": "Test", "steps": [{"action": "wait"}]}
            save_autosave(scenario)
            loaded = load_autosave()
            assert loaded == scenario
            clear_autosave()
            assert load_autosave() is None
        finally:
            mod.AUTOSAVE_DIR = original_dir

    def test_has_recovery(self):
        from neurascreen.gui.advanced.autosave import has_recovery, save_autosave, clear_autosave
        import neurascreen.gui.advanced.autosave as mod

        original_dir = mod.AUTOSAVE_DIR
        mod.AUTOSAVE_DIR = Path(tempfile.mkdtemp()) / "autosave"

        try:
            assert not has_recovery()
            save_autosave({"title": "X", "steps": []})
            assert has_recovery()
            clear_autosave()
            assert not has_recovery()
        finally:
            mod.AUTOSAVE_DIR = original_dir

    def test_autosave_timestamp(self):
        from neurascreen.gui.advanced.autosave import (
            save_autosave, autosave_timestamp, clear_autosave,
        )
        import neurascreen.gui.advanced.autosave as mod
        import time

        original_dir = mod.AUTOSAVE_DIR
        mod.AUTOSAVE_DIR = Path(tempfile.mkdtemp()) / "autosave"

        try:
            save_autosave({"title": "T", "steps": []})
            ts = autosave_timestamp()
            assert abs(ts - int(time.time())) < 5
            clear_autosave()
        finally:
            mod.AUTOSAVE_DIR = original_dir

    def test_load_nonexistent(self):
        from neurascreen.gui.advanced.autosave import load_autosave
        import neurascreen.gui.advanced.autosave as mod

        original_dir = mod.AUTOSAVE_DIR
        mod.AUTOSAVE_DIR = Path(tempfile.mkdtemp()) / "nonexistent"

        try:
            assert load_autosave() is None
        finally:
            mod.AUTOSAVE_DIR = original_dir


class TestExtractTargets:
    """Test selector extraction from steps."""

    def test_empty(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        assert extract_targets([]) == []

    def test_click_selector(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        steps = [
            {"action": "navigate", "url": "/page"},
            {"action": "click", "selector": "#btn"},
        ]
        targets = extract_targets(steps)
        assert len(targets) == 1
        assert targets[0]["target"] == "#btn"
        assert targets[0]["target_type"] == "selector"
        assert targets[0]["url"] == "/page"

    def test_click_text(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        steps = [
            {"action": "click_text", "text": "Save"},
        ]
        targets = extract_targets(steps)
        assert len(targets) == 1
        assert targets[0]["target"] == "Save"
        assert targets[0]["target_type"] == "text"

    def test_skips_non_selector_actions(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        steps = [
            {"action": "wait", "duration": 1000},
            {"action": "scroll", "direction": "down"},
            {"action": "navigate", "url": "/x"},
        ]
        targets = extract_targets(steps)
        assert len(targets) == 0

    def test_tracks_url_changes(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        steps = [
            {"action": "navigate", "url": "/a"},
            {"action": "click", "selector": "#x"},
            {"action": "navigate", "url": "/b"},
            {"action": "click", "selector": "#y"},
        ]
        targets = extract_targets(steps)
        assert targets[0]["url"] == "/a"
        assert targets[1]["url"] == "/b"

    def test_type_action(self):
        from neurascreen.gui.advanced.selector_validator import extract_targets
        steps = [
            {"action": "type", "selector": "input#name", "text": "hello"},
        ]
        targets = extract_targets(steps)
        assert len(targets) == 1
        assert targets[0]["action"] == "type"


class TestSelectorValidatorImport:
    """Test imports work."""

    def test_dialog_import(self):
        from neurascreen.gui.advanced.selector_validator import SelectorValidatorDialog
        assert hasattr(SelectorValidatorDialog, "step_requested")

    def test_validator_thread_import(self):
        from neurascreen.gui.advanced.selector_validator import ValidatorThread
        assert hasattr(ValidatorThread, "result_ready")


class TestStatisticsDialogImport:
    def test_import(self):
        from neurascreen.gui.advanced.statistics import StatisticsDialog
        assert StatisticsDialog is not None


class TestDiffDialogImport:
    def test_import(self):
        from neurascreen.gui.advanced.diff_viewer import DiffDialog
        assert DiffDialog is not None


class TestAutosaveManagerImport:
    def test_import(self):
        from neurascreen.gui.advanced.autosave import AutosaveManager
        assert AutosaveManager is not None
