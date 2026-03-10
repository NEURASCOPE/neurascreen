"""Tests for utility helpers."""

import logging
from pathlib import Path

import pytest

from neurascreen.utils import slugify, format_duration, setup_logger


class TestSlugify:
    """Tests for slugify()."""

    def test_simple(self):
        assert slugify("Hello World") == "hello_world"

    def test_accents(self):
        assert slugify("Présentation générale") == "presentation_generale"

    def test_all_accents(self):
        assert slugify("àâä éèêë îï ôö ùûü ç") == "aaa_eeee_ii_oo_uuu_c"

    def test_special_chars(self):
        assert slugify("Hello! @World #2024") == "hello_world_2024"

    def test_dashes_and_spaces(self):
        assert slugify("my - video - demo") == "my_video_demo"

    def test_leading_trailing_underscores(self):
        assert slugify("  --hello--  ") == "hello"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_chars(self):
        assert slugify("@#$%") == ""

    def test_numbers(self):
        assert slugify("Video 01 - Dashboard") == "video_01_dashboard"

    def test_unicode_passthrough(self):
        # Characters not in the accent map get stripped
        assert slugify("日本語") == ""


class TestFormatDuration:
    """Tests for format_duration()."""

    def test_seconds_only(self):
        assert format_duration(5000) == "5s"

    def test_zero(self):
        assert format_duration(0) == "0s"

    def test_minutes_and_seconds(self):
        assert format_duration(125000) == "2m05s"

    def test_exact_minute(self):
        assert format_duration(60000) == "1m00s"

    def test_sub_second(self):
        assert format_duration(500) == "0s"

    def test_large_duration(self):
        assert format_duration(3600000) == "60m00s"


class TestSetupLogger:
    """Tests for setup_logger()."""

    def test_creates_logger(self, tmp_path):
        logger = setup_logger("test_logger_1", tmp_path, verbose=False)
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO

    def test_verbose_mode(self, tmp_path):
        logger = setup_logger("test_logger_2", tmp_path, verbose=True)
        assert logger.level == logging.DEBUG

    def test_creates_log_file(self, tmp_path):
        setup_logger("test_logger_3", tmp_path)
        log_files = list(tmp_path.glob("run_*.log"))
        assert len(log_files) == 1

    def test_idempotent(self, tmp_path):
        logger1 = setup_logger("test_logger_4", tmp_path)
        handler_count = len(logger1.handlers)
        logger2 = setup_logger("test_logger_4", tmp_path)
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count
