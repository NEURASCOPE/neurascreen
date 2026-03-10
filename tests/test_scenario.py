"""Tests for scenario parser and validator."""

import json
import tempfile
from pathlib import Path

import pytest

from neurascreen.scenario import validate_scenario, parse_scenario, VALID_ACTIONS


class TestValidateScenario:
    """Tests for validate_scenario()."""

    def test_valid_minimal(self):
        data = {
            "title": "Test",
            "steps": [
                {"action": "navigate", "url": "/home"}
            ]
        }
        assert validate_scenario(data) == []

    def test_valid_all_actions(self):
        data = {
            "title": "Test all actions",
            "steps": [
                {"action": "navigate", "url": "/"},
                {"action": "click", "selector": "#btn"},
                {"action": "click_text", "text": "Submit"},
                {"action": "type", "selector": "input", "text": "hello"},
                {"action": "scroll", "selector": "main", "direction": "down"},
                {"action": "hover", "selector": ".menu"},
                {"action": "key", "text": "Enter"},
                {"action": "wait", "duration": 1000},
                {"action": "drag", "text": "Item"},
                {"action": "delete_node"},
                {"action": "close_modal"},
                {"action": "zoom_out"},
                {"action": "fit_view"},
            ]
        }
        assert validate_scenario(data) == []

    def test_missing_title(self):
        data = {"steps": [{"action": "wait"}]}
        errors = validate_scenario(data)
        assert any("title" in e for e in errors)

    def test_missing_steps(self):
        data = {"title": "Test"}
        errors = validate_scenario(data)
        assert any("steps" in e for e in errors)

    def test_empty_steps(self):
        data = {"title": "Test", "steps": []}
        errors = validate_scenario(data)
        assert any("at least one step" in e for e in errors)

    def test_invalid_action(self):
        data = {"title": "Test", "steps": [{"action": "fly"}]}
        errors = validate_scenario(data)
        assert any("invalid action" in e for e in errors)

    def test_missing_action(self):
        data = {"title": "Test", "steps": [{"selector": "#btn"}]}
        errors = validate_scenario(data)
        assert any("action" in e for e in errors)

    def test_navigate_requires_url(self):
        data = {"title": "Test", "steps": [{"action": "navigate"}]}
        errors = validate_scenario(data)
        assert any("url" in e for e in errors)

    def test_click_requires_selector(self):
        data = {"title": "Test", "steps": [{"action": "click"}]}
        errors = validate_scenario(data)
        assert any("selector" in e for e in errors)

    def test_click_text_requires_text(self):
        data = {"title": "Test", "steps": [{"action": "click_text"}]}
        errors = validate_scenario(data)
        assert any("text" in e for e in errors)

    def test_type_requires_selector_and_text(self):
        data = {"title": "Test", "steps": [{"action": "type"}]}
        errors = validate_scenario(data)
        assert any("selector" in e for e in errors)

    def test_scroll_requires_selector(self):
        data = {"title": "Test", "steps": [{"action": "scroll"}]}
        errors = validate_scenario(data)
        assert any("selector" in e for e in errors)

    def test_scroll_invalid_direction(self):
        data = {"title": "Test", "steps": [
            {"action": "scroll", "selector": "main", "direction": "left"}
        ]}
        errors = validate_scenario(data)
        assert any("direction" in e for e in errors)

    def test_drag_requires_text(self):
        data = {"title": "Test", "steps": [{"action": "drag"}]}
        errors = validate_scenario(data)
        assert any("text" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_scenario("not a dict")
        assert any("JSON object" in e for e in errors)

    def test_step_not_a_dict(self):
        data = {"title": "Test", "steps": ["not a dict"]}
        errors = validate_scenario(data)
        assert any("must be an object" in e for e in errors)


class TestParseScenario:
    """Tests for parse_scenario()."""

    def test_parse_valid_file(self, tmp_path):
        data = {
            "title": "My Demo",
            "description": "A test demo",
            "resolution": {"width": 1920, "height": 1080},
            "steps": [
                {"action": "navigate", "url": "/", "wait": 2000},
                {"action": "wait", "duration": 3000, "narration": "Hello world"},
            ]
        }
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))

        scenario = parse_scenario(str(f))
        assert scenario.title == "My Demo"
        assert scenario.description == "A test demo"
        assert scenario.width == 1920
        assert scenario.height == 1080
        assert len(scenario.steps) == 2
        assert scenario.steps[0].action == "navigate"
        assert scenario.steps[0].url == "/"
        assert scenario.steps[0].wait == 2000
        assert scenario.steps[1].narration == "Hello world"
        assert scenario.steps[1].duration == 3000

    def test_parse_defaults(self, tmp_path):
        data = {
            "title": "Minimal",
            "steps": [{"action": "wait"}]
        }
        f = tmp_path / "minimal.json"
        f.write_text(json.dumps(data))

        scenario = parse_scenario(str(f))
        step = scenario.steps[0]
        assert step.wait == 1000
        assert step.duration == 1000
        assert step.narration == ""
        assert step.delay == 50
        assert step.amount == 300

    def test_parse_missing_file(self):
        with pytest.raises(FileNotFoundError):
            parse_scenario("/nonexistent/file.json")

    def test_parse_invalid_scenario(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"title": "Bad", "steps": [{"action": "fly"}]}))
        with pytest.raises(ValueError, match="Invalid scenario"):
            parse_scenario(str(f))

    def test_parse_invalid_json(self, tmp_path):
        f = tmp_path / "broken.json"
        f.write_text("not json {{{")
        with pytest.raises(Exception):
            parse_scenario(str(f))


class TestExampleScenarios:
    """Validate all example scenarios shipped with the project."""

    def _get_examples(self):
        root = Path(__file__).parent.parent / "examples"
        return sorted(root.rglob("*.json"))

    def test_all_examples_are_valid(self):
        examples = self._get_examples()
        assert len(examples) > 0, "No example scenarios found"
        for f in examples:
            with open(f) as fh:
                data = json.load(fh)
            errors = validate_scenario(data)
            assert errors == [], f"{f.name}: {errors}"

    def test_all_examples_parse(self):
        examples = self._get_examples()
        for f in examples:
            scenario = parse_scenario(str(f))
            assert scenario.title
            assert len(scenario.steps) > 0
