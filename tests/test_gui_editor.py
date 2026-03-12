"""Tests for the GUI editor components (non-Qt, logic only)."""

import json
import copy

import pytest


class TestUndoCommands:
    """Tests for undo/redo command classes."""

    def test_add_step(self):
        from neurascreen.gui.editor.undo_commands import AddStepCommand
        steps = [{"action": "navigate", "url": "/"}]
        cmd = AddStepCommand(steps, 1, {"action": "wait", "duration": 1000})
        cmd.redo()
        assert len(steps) == 2
        assert steps[1]["action"] == "wait"
        cmd.undo()
        assert len(steps) == 1

    def test_add_step_at_beginning(self):
        from neurascreen.gui.editor.undo_commands import AddStepCommand
        steps = [{"action": "navigate", "url": "/"}]
        cmd = AddStepCommand(steps, 0, {"action": "wait", "duration": 500})
        cmd.redo()
        assert len(steps) == 2
        assert steps[0]["action"] == "wait"
        assert steps[1]["action"] == "navigate"
        cmd.undo()
        assert len(steps) == 1
        assert steps[0]["action"] == "navigate"

    def test_delete_step(self):
        from neurascreen.gui.editor.undo_commands import DeleteStepCommand
        steps = [{"action": "navigate"}, {"action": "wait"}, {"action": "click"}]
        cmd = DeleteStepCommand(steps, 1)
        cmd.redo()
        assert len(steps) == 2
        assert steps[1]["action"] == "click"
        cmd.undo()
        assert len(steps) == 3
        assert steps[1]["action"] == "wait"

    def test_edit_step(self):
        from neurascreen.gui.editor.undo_commands import EditStepCommand
        steps = [{"action": "navigate", "url": "/old"}]
        cmd = EditStepCommand(steps, 0, {"action": "navigate", "url": "/new"})
        cmd.redo()
        assert steps[0]["url"] == "/new"
        cmd.undo()
        assert steps[0]["url"] == "/old"

    def test_move_step(self):
        from neurascreen.gui.editor.undo_commands import MoveStepCommand
        steps = [{"action": "a"}, {"action": "b"}, {"action": "c"}]
        cmd = MoveStepCommand(steps, 0, 2)
        cmd.redo()
        assert [s["action"] for s in steps] == ["b", "c", "a"]
        cmd.undo()
        assert [s["action"] for s in steps] == ["a", "b", "c"]

    def test_bulk_delete(self):
        from neurascreen.gui.editor.undo_commands import BulkDeleteCommand
        steps = [{"action": "a"}, {"action": "b"}, {"action": "c"}, {"action": "d"}]
        cmd = BulkDeleteCommand(steps, [1, 3])
        cmd.redo()
        assert len(steps) == 2
        assert [s["action"] for s in steps] == ["a", "c"]
        cmd.undo()
        assert len(steps) == 4
        assert [s["action"] for s in steps] == ["a", "b", "c", "d"]

    def test_edit_metadata(self):
        from neurascreen.gui.editor.undo_commands import EditMetadataCommand
        meta = {"title": "Old"}
        cmd = EditMetadataCommand(meta, "title", "Old", "New")
        cmd.redo()
        assert meta["title"] == "New"
        cmd.undo()
        assert meta["title"] == "Old"


class TestStepTemplates:
    """Tests for step templates."""

    def test_get_template_names(self):
        from neurascreen.gui.editor.step_templates import get_template_names
        names = get_template_names()
        assert len(names) >= 5
        assert "Navigation + Narration" in names
        assert "Introduction" in names
        assert "Conclusion" in names

    def test_get_template_steps(self):
        from neurascreen.gui.editor.step_templates import get_template_steps
        steps = get_template_steps("Navigation + Narration")
        assert len(steps) == 2
        assert steps[0]["action"] == "navigate"
        assert steps[1]["action"] == "wait"
        assert "narration" in steps[1]

    def test_template_is_deep_copy(self):
        from neurascreen.gui.editor.step_templates import get_template_steps
        steps1 = get_template_steps("Introduction")
        steps2 = get_template_steps("Introduction")
        steps1[0]["narration"] = "modified"
        assert steps2[0]["narration"] != "modified"

    def test_unknown_template(self):
        from neurascreen.gui.editor.step_templates import get_template_steps
        steps = get_template_steps("nonexistent")
        assert steps == []

    def test_drag_template_has_7_steps(self):
        from neurascreen.gui.editor.step_templates import get_template_steps
        steps = get_template_steps("Drag + Configure + Delete")
        assert len(steps) == 7
        actions = [s["action"] for s in steps]
        assert "drag" in actions
        assert "fit_view" in actions
        assert "close_modal" in actions
        assert "delete_node" in actions


class TestStepDetailFields:
    """Tests for action field definitions."""

    def test_all_actions_have_fields(self):
        from neurascreen.gui.editor.step_detail import ACTION_FIELDS
        from neurascreen.scenario import VALID_ACTIONS
        for action in VALID_ACTIONS:
            assert action in ACTION_FIELDS, f"Missing ACTION_FIELDS for '{action}'"

    def test_all_actions_have_colors(self):
        from neurascreen.gui.editor.step_detail import ACTION_COLORS
        from neurascreen.scenario import VALID_ACTIONS
        for action in VALID_ACTIONS:
            assert action in ACTION_COLORS, f"Missing ACTION_COLORS for '{action}'"

    def test_navigate_fields(self):
        from neurascreen.gui.editor.step_detail import ACTION_FIELDS
        assert ACTION_FIELDS["navigate"] == ["url"]

    def test_type_fields(self):
        from neurascreen.gui.editor.step_detail import ACTION_FIELDS
        assert "selector" in ACTION_FIELDS["type"]
        assert "text" in ACTION_FIELDS["type"]
        assert "delay" in ACTION_FIELDS["type"]

    def test_wait_fields(self):
        from neurascreen.gui.editor.step_detail import ACTION_FIELDS
        assert ACTION_FIELDS["wait"] == ["duration"]

    def test_no_param_actions(self):
        from neurascreen.gui.editor.step_detail import ACTION_FIELDS
        assert ACTION_FIELDS["delete_node"] == []
        assert ACTION_FIELDS["close_modal"] == []
        assert ACTION_FIELDS["fit_view"] == []


class TestSyntaxHighlighter:
    """Tests for JSON syntax highlighter (pattern-only, no Qt)."""

    def test_import(self):
        from neurascreen.gui.editor.syntax_highlighter import JsonHighlighter
        assert JsonHighlighter is not None
