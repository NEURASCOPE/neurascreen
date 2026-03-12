"""Tests for macro recorder event-to-step conversion."""

import json
from pathlib import Path

import pytest

from neurascreen.macro import _events_to_steps


class TestEventsToSteps:
    """Tests for converting raw browser events to scenario steps."""

    def test_empty_events_creates_navigate(self):
        steps = _events_to_steps([], "http://localhost:3000/dashboard")
        assert len(steps) == 1
        assert steps[0]["action"] == "navigate"
        assert steps[0]["url"] == "/dashboard"

    def test_navigate_event(self):
        events = [
            {"type": "navigate", "timestamp": 1000, "url": "/settings"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "navigate"
        assert steps[0]["url"] == "/settings"

    def test_duplicate_navigate_skipped(self):
        events = [
            {"type": "navigate", "timestamp": 1000, "url": "/page"},
            {"type": "navigate", "timestamp": 1500, "url": "/page"},
            {"type": "navigate", "timestamp": 2000, "url": "/other"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/page")
        # Duplicate /page navigations are skipped, only /other remains
        navigate_steps = [s for s in steps if s["action"] == "navigate"]
        assert len(navigate_steps) == 1
        assert navigate_steps[0]["url"] == "/other"

    def test_click_with_text_uses_click_text(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "Save", "selector": "button.save", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "click_text"
        assert steps[0]["text"] == "Save"

    def test_click_without_text_uses_selector(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "", "selector": "#icon-btn", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "click"
        assert steps[0]["selector"] == "#icon-btn"

    def test_click_long_text_uses_selector(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "A" * 60, "selector": ".card", "tag": "div", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "click"
        assert steps[0]["selector"] == ".card"

    def test_scroll_event(self):
        events = [
            {"type": "scroll", "timestamp": 1000, "scrollY": 400, "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "scroll"
        assert steps[0]["direction"] == "down"

    def test_key_event(self):
        events = [
            {"type": "key", "timestamp": 1000, "key": "Enter", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert steps[0]["action"] == "key"
        assert steps[0]["text"] == "Enter"

    def test_pause_creates_wait_step(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "A", "selector": ".a", "tag": "button", "url": "/"},
            {"type": "click", "timestamp": 5000, "text": "B", "selector": ".b", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert len(steps) == 3
        assert steps[1]["action"] == "wait"
        assert steps[1]["duration"] == 4000

    def test_pause_capped_at_10s(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "A", "selector": ".a", "tag": "button", "url": "/"},
            {"type": "click", "timestamp": 30000, "text": "B", "selector": ".b", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        wait_step = [s for s in steps if s["action"] == "wait"][0]
        assert wait_step["duration"] == 10000

    def test_short_pause_no_wait_step(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "A", "selector": ".a", "tag": "button", "url": "/"},
            {"type": "click", "timestamp": 2500, "text": "B", "selector": ".b", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        assert all(s["action"] != "wait" for s in steps)

    def test_mixed_events_order(self):
        events = [
            {"type": "navigate", "timestamp": 1000, "url": "/page1"},
            {"type": "click", "timestamp": 2000, "text": "OK", "selector": ".ok", "tag": "button", "url": "/page1"},
            {"type": "scroll", "timestamp": 2500, "scrollY": 300, "url": "/page1"},
            {"type": "key", "timestamp": 3000, "key": "Escape", "url": "/page1"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        actions = [s["action"] for s in steps]
        assert actions == ["navigate", "click_text", "scroll", "key"]

    def test_base_url_path_extracted(self):
        steps = _events_to_steps([], "http://localhost:3000/app/dashboard?tab=1")
        assert steps[0]["url"] == "/app/dashboard"

    def test_narration_always_empty(self):
        events = [
            {"type": "click", "timestamp": 1000, "text": "Go", "selector": ".go", "tag": "button", "url": "/"},
        ]
        steps = _events_to_steps(events, "http://localhost:3000/")
        for step in steps:
            if "narration" in step:
                assert step["narration"] == ""
