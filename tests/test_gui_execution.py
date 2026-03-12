"""Tests for the GUI execution components (logic only, no Qt event loop)."""

import sys

import pytest


class TestCommandRunnerBuild:
    """Tests for CommandRunner command building."""

    def test_build_validate(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("validate", "/path/to/scenario.json")
        cmd = runner._build_command()
        assert cmd[-2] == "validate"
        assert cmd[-1] == "/path/to/scenario.json"
        assert sys.executable == cmd[0]
        assert "-m" in cmd
        assert "neurascreen" in cmd

    def test_build_full_with_options(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("full", "/path/to/s.json", {
            "srt": True,
            "chapters": True,
            "headless": True,
            "verbose": True,
        })
        cmd = runner._build_command()
        assert "-v" in cmd
        assert "--headless" in cmd
        assert "full" in cmd
        assert "--srt" in cmd
        assert "--chapters" in cmd

    def test_build_run_no_options(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("run", "/s.json", {})
        cmd = runner._build_command()
        assert "--srt" not in cmd
        assert "--chapters" not in cmd
        assert "-v" not in cmd
        assert "--headless" not in cmd

    def test_build_preview_ignores_srt(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("preview", "/s.json", {"srt": True, "chapters": True})
        cmd = runner._build_command()
        # preview doesn't support --srt/--chapters
        assert "--srt" not in cmd
        assert "--chapters" not in cmd

    def test_build_validate_ignores_srt(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("validate", "/s.json", {"srt": True})
        cmd = runner._build_command()
        assert "--srt" not in cmd

    def test_build_with_output_path(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("full", "/s.json", {"output": "/out/video.mp4"})
        cmd = runner._build_command()
        assert "-o" in cmd
        idx = cmd.index("-o")
        assert cmd[idx + 1] == "/out/video.mp4"

    def test_cancel_before_start(self):
        from neurascreen.gui.execution.runner import CommandRunner
        runner = CommandRunner("validate", "/s.json")
        # Should not raise
        runner.cancel()
        assert runner._cancelled is True


class TestConsoleWidget:
    """Tests for console widget import."""

    def test_import(self):
        from neurascreen.gui.execution.console import ConsoleWidget
        assert ConsoleWidget is not None


class TestRunPanel:
    """Tests for run panel import."""

    def test_import(self):
        from neurascreen.gui.execution.run_panel import RunPanel
        assert RunPanel is not None
