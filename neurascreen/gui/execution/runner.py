"""Background runner: executes CLI commands in a QThread via subprocess."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("neurascreen.gui")


class CommandRunner(QThread):
    """Runs a neurascreen CLI command in a subprocess and streams output."""

    line_output = Signal(str)   # each line of stdout/stderr
    finished_ok = Signal()      # command succeeded
    finished_error = Signal(str)  # command failed with message
    progress = Signal(str)      # status update (e.g. "Step 5/42")

    def __init__(
        self,
        command: str,
        scenario_path: str,
        options: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._command = command
        self._scenario_path = scenario_path
        self._options = options or {}
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    def run(self) -> None:
        """Execute the command in a subprocess."""
        cmd = self._build_command()
        self.line_output.emit(f"$ {' '.join(cmd)}")
        self.line_output.emit("")

        try:
            # Build environment: force headed mode unless headless is checked
            import os
            env = os.environ.copy()
            if not self._options.get("headless"):
                env["BROWSER_HEADLESS"] = "false"

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(Path(self._scenario_path).parent.parent),
                env=env,
            )

            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                line = line.rstrip("\n\r")
                if line:
                    self.line_output.emit(line)
                    # Detect step progress
                    if line.strip().startswith("[") and "/" in line and "]" in line:
                        try:
                            bracket = line.split("]")[0].split("[")[-1]
                            self.progress.emit(f"Step {bracket}")
                        except (IndexError, ValueError):
                            pass

            self._process.stdout.close()
            returncode = self._process.wait()

            if self._cancelled:
                self.line_output.emit("\n--- Cancelled ---")
                self.finished_error.emit("Cancelled by user")
            elif returncode == 0:
                self.finished_ok.emit()
            else:
                self.finished_error.emit(f"Exit code {returncode}")

        except FileNotFoundError:
            self.finished_error.emit("neurascreen command not found")
        except Exception as e:
            self.finished_error.emit(str(e))
        finally:
            self._process = None

    def cancel(self) -> None:
        """Cancel the running command."""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            except OSError:
                pass

    def _build_command(self) -> list[str]:
        """Build the full CLI command list."""
        # Use the same Python that's running the GUI
        python = sys.executable
        cmd = [python, "-m", "neurascreen"]

        # Verbose
        if self._options.get("verbose"):
            cmd.append("-v")

        # Headless
        if self._options.get("headless"):
            cmd.append("--headless")

        # Command
        cmd.append(self._command)

        # Scenario path
        cmd.append(self._scenario_path)

        # Command-specific options
        if self._options.get("srt") and self._command in ("run", "full"):
            cmd.append("--srt")
        if self._options.get("chapters") and self._command in ("run", "full"):
            cmd.append("--chapters")
        if self._options.get("output") and self._command in ("run", "full"):
            cmd.extend(["-o", self._options["output"]])

        return cmd
