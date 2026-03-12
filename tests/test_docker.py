"""Tests for Docker configuration files."""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


class TestDockerFiles:
    """Verify Docker configuration files exist and are well-formed."""

    def test_dockerfile_exists(self):
        assert (PROJECT_ROOT / "Dockerfile").exists()

    def test_dockerfile_has_from(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert content.startswith("FROM ")

    def test_dockerfile_installs_ffmpeg(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "ffmpeg" in content

    def test_dockerfile_installs_xvfb(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "xvfb" in content.lower() or "Xvfb" in content

    def test_dockerfile_installs_playwright(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "playwright install" in content

    def test_dockerfile_sets_display(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "DISPLAY" in content

    def test_entrypoint_exists(self):
        assert (PROJECT_ROOT / "docker-entrypoint.sh").exists()

    def test_entrypoint_starts_xvfb(self):
        content = (PROJECT_ROOT / "docker-entrypoint.sh").read_text()
        assert "Xvfb" in content

    def test_entrypoint_execs_neurascreen(self):
        content = (PROJECT_ROOT / "docker-entrypoint.sh").read_text()
        assert "exec neurascreen" in content

    def test_dockerignore_exists(self):
        assert (PROJECT_ROOT / ".dockerignore").exists()

    def test_dockerignore_excludes_venv(self):
        content = (PROJECT_ROOT / ".dockerignore").read_text()
        assert ".venv" in content

    def test_dockerignore_excludes_env(self):
        content = (PROJECT_ROOT / ".dockerignore").read_text()
        assert ".env" in content
