"""Tests for the macro recorder GUI module (logic only, no Qt)."""


class TestCleanupDedupClicks:
    """Test dedup_clicks cleanup function."""

    def test_empty_list(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        assert dedup_clicks([]) == []

    def test_no_duplicates(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "text": "A", "timestamp": 1000},
            {"type": "click", "text": "B", "timestamp": 2000},
        ]
        assert len(dedup_clicks(events)) == 2

    def test_removes_duplicate_by_text(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "text": "Save", "timestamp": 1000},
            {"type": "click", "text": "Save", "timestamp": 1100},
        ]
        result = dedup_clicks(events)
        assert len(result) == 1
        assert result[0]["text"] == "Save"

    def test_removes_duplicate_by_selector(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "selector": "#btn", "text": "", "timestamp": 1000},
            {"type": "click", "selector": "#btn", "text": "", "timestamp": 1200},
        ]
        result = dedup_clicks(events)
        assert len(result) == 1

    def test_keeps_clicks_beyond_threshold(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "text": "Save", "timestamp": 1000},
            {"type": "click", "text": "Save", "timestamp": 2000},
        ]
        result = dedup_clicks(events, threshold_ms=300)
        assert len(result) == 2

    def test_keeps_different_targets(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "text": "Save", "timestamp": 1000},
            {"type": "click", "text": "Cancel", "timestamp": 1100},
        ]
        result = dedup_clicks(events)
        assert len(result) == 2

    def test_non_click_events_kept(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "navigate", "url": "/a", "timestamp": 1000},
            {"type": "navigate", "url": "/b", "timestamp": 1100},
        ]
        result = dedup_clicks(events)
        assert len(result) == 2

    def test_triple_rapid_click(self):
        from neurascreen.gui.macro.cleanup import dedup_clicks
        events = [
            {"type": "click", "text": "X", "timestamp": 1000},
            {"type": "click", "text": "X", "timestamp": 1050},
            {"type": "click", "text": "X", "timestamp": 1100},
        ]
        result = dedup_clicks(events)
        assert len(result) == 1


class TestCleanupMergeNavigations:
    """Test merge_navigations cleanup function."""

    def test_empty_list(self):
        from neurascreen.gui.macro.cleanup import merge_navigations
        assert merge_navigations([]) == []

    def test_no_consecutive_navs(self):
        from neurascreen.gui.macro.cleanup import merge_navigations
        events = [
            {"type": "navigate", "url": "/a"},
            {"type": "click", "text": "X"},
            {"type": "navigate", "url": "/b"},
        ]
        result = merge_navigations(events)
        assert len(result) == 3

    def test_merges_consecutive_navs(self):
        from neurascreen.gui.macro.cleanup import merge_navigations
        events = [
            {"type": "navigate", "url": "/a", "timestamp": 1000},
            {"type": "navigate", "url": "/b", "timestamp": 1500},
            {"type": "navigate", "url": "/c", "timestamp": 2000},
        ]
        result = merge_navigations(events)
        assert len(result) == 1
        assert result[0]["url"] == "/c"

    def test_preserves_non_nav_events(self):
        from neurascreen.gui.macro.cleanup import merge_navigations
        events = [
            {"type": "click", "text": "A"},
            {"type": "scroll", "scrollY": 100},
        ]
        result = merge_navigations(events)
        assert len(result) == 2


class TestCleanupCapWaits:
    """Test cap_waits cleanup function."""

    def test_empty_list(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        assert cap_waits([]) == []

    def test_caps_long_wait(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        steps = [{"action": "wait", "duration": 15000}]
        result = cap_waits(steps)
        assert result[0]["duration"] == 5000

    def test_removes_short_wait(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        steps = [{"action": "wait", "duration": 200}]
        result = cap_waits(steps)
        assert len(result) == 0

    def test_keeps_normal_wait(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        steps = [{"action": "wait", "duration": 3000}]
        result = cap_waits(steps)
        assert len(result) == 1
        assert result[0]["duration"] == 3000

    def test_non_wait_steps_unchanged(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        steps = [
            {"action": "click", "selector": "#x"},
            {"action": "navigate", "url": "/y"},
        ]
        result = cap_waits(steps)
        assert len(result) == 2

    def test_works_on_raw_events_with_type(self):
        from neurascreen.gui.macro.cleanup import cap_waits
        events = [{"type": "wait", "duration": 100}]
        result = cap_waits(events)
        assert len(result) == 0


class TestCleanupPipeline:
    """Test full cleanup pipeline."""

    def test_cleanup_events_all_passes(self):
        from neurascreen.gui.macro.cleanup import cleanup_events
        events = [
            {"type": "navigate", "url": "/a", "timestamp": 1000},
            {"type": "navigate", "url": "/b", "timestamp": 1100},
            {"type": "click", "text": "X", "timestamp": 2000},
            {"type": "click", "text": "X", "timestamp": 2050},
        ]
        result = cleanup_events(events)
        assert len(result) == 2
        assert result[0]["type"] == "navigate"
        assert result[0]["url"] == "/b"
        assert result[1]["type"] == "click"

    def test_cleanup_steps(self):
        from neurascreen.gui.macro.cleanup import cleanup_steps
        steps = [
            {"action": "wait", "duration": 100},
            {"action": "click", "selector": "#x"},
            {"action": "wait", "duration": 20000},
        ]
        result = cleanup_steps(steps)
        assert len(result) == 2
        assert result[0]["action"] == "click"
        assert result[1]["duration"] == 5000


class TestEventFeedFormat:
    """Test event formatting for the feed display."""

    def test_format_click_with_text(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "click", "text": "Save", "selector": "#btn"})
        assert "[click]" in result
        assert "Save" in result

    def test_format_click_with_selector(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "click", "text": "", "selector": "#btn-ok"})
        assert "[click]" in result
        assert "#btn-ok" in result

    def test_format_navigate(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "navigate", "url": "/customer"})
        assert "[navigate]" in result
        assert "/customer" in result

    def test_format_scroll(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "scroll", "scrollY": 500})
        assert "[scroll]" in result
        assert "500" in result

    def test_format_key(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "key", "key": "Enter"})
        assert "[key]" in result
        assert "Enter" in result

    def test_format_unknown(self):
        from neurascreen.gui.macro.event_feed import format_event
        result = format_event({"type": "custom", "data": 42})
        assert "[custom]" in result


class TestRecorderDialogBuildScenario:
    """Test scenario building from recorded data."""

    def test_build_scenario_structure(self):
        from neurascreen.gui.macro.recorder_dialog import RecorderDialog
        # Verify the class is importable and has expected attributes
        assert hasattr(RecorderDialog, "scenario_ready")
        assert hasattr(RecorderDialog, "_build_scenario")

    def test_same_target_by_text(self):
        from neurascreen.gui.macro.cleanup import _same_target
        a = {"text": "Save", "selector": "#a"}
        b = {"text": "Save", "selector": "#b"}
        assert _same_target(a, b) is True

    def test_same_target_by_selector(self):
        from neurascreen.gui.macro.cleanup import _same_target
        a = {"text": "", "selector": "#btn"}
        b = {"text": "", "selector": "#btn"}
        assert _same_target(a, b) is True

    def test_different_targets(self):
        from neurascreen.gui.macro.cleanup import _same_target
        a = {"text": "Save", "selector": "#a"}
        b = {"text": "Cancel", "selector": "#b"}
        assert _same_target(a, b) is False

    def test_no_matching_fields(self):
        from neurascreen.gui.macro.cleanup import _same_target
        a = {"text": "", "selector": ""}
        b = {"text": "", "selector": ""}
        assert _same_target(a, b) is False


class TestRecorderThreadImport:
    """Test RecorderThread is importable and has expected signals."""

    def test_import(self):
        from neurascreen.gui.macro.recorder_dialog import RecorderThread
        assert hasattr(RecorderThread, "event_captured")
        assert hasattr(RecorderThread, "recording_finished")
        assert hasattr(RecorderThread, "recording_error")
        assert hasattr(RecorderThread, "status_changed")


class TestEventFeedImport:
    """Test EventFeed is importable."""

    def test_import(self):
        from neurascreen.gui.macro.event_feed import EventFeed
        assert EventFeed is not None

    def test_event_colors_defined(self):
        from neurascreen.gui.macro.event_feed import EVENT_COLORS
        assert "click" in EVENT_COLORS
        assert "navigate" in EVENT_COLORS
        assert "scroll" in EVENT_COLORS
        assert "key" in EVENT_COLORS
