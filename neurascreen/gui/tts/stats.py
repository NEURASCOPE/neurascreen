"""Narration statistics — pure logic, no Qt dependency."""

from dataclasses import dataclass


WORDS_PER_MINUTE = 130


@dataclass
class NarrationStats:
    """Statistics for scenario narration."""

    total_steps: int
    narrated_steps: int
    word_count: int
    estimated_reading_ms: int
    total_wait_ms: int

    @property
    def narrated_ratio(self) -> str:
        return f"{self.narrated_steps}/{self.total_steps}"

    @property
    def estimated_reading_s(self) -> float:
        return self.estimated_reading_ms / 1000

    @property
    def total_duration_s(self) -> float:
        return (self.estimated_reading_ms + self.total_wait_ms) / 1000

    def format_duration(self, ms: int) -> str:
        s = ms / 1000
        minutes = int(s // 60)
        seconds = int(s % 60)
        if minutes > 0:
            return f"{minutes}m {seconds:02d}s"
        return f"{seconds}s"


def compute_stats(steps: list[dict]) -> NarrationStats:
    """Compute narration statistics from a list of step dicts."""
    total = len(steps)
    narrated = 0
    word_count = 0
    total_wait = 0

    for step in steps:
        narration = step.get("narration", "").strip()
        if narration:
            narrated += 1
            word_count += len(narration.split())

        wait = step.get("wait", 0)
        duration = step.get("duration", 0)
        total_wait += wait + duration

    # Estimated reading time at WORDS_PER_MINUTE
    estimated_ms = int((word_count / WORDS_PER_MINUTE) * 60 * 1000) if word_count > 0 else 0

    return NarrationStats(
        total_steps=total,
        narrated_steps=narrated,
        word_count=word_count,
        estimated_reading_ms=estimated_ms,
        total_wait_ms=total_wait,
    )
