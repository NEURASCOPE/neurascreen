"""Pronunciation helper — substitution table for TTS.

Pure logic (no Qt). The GUI table widget is built separately.
Stores substitutions in ~/.neurascreen/pronunciation.json.
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger("neurascreen.gui")

DEFAULT_FILE = Path.home() / ".neurascreen" / "pronunciation.json"

# Built-in substitutions (Gradium-specific, can be overridden)
BUILTIN_SUBSTITUTIONS = [
    ("flux", "flu", "Gradium reads 'fluxe'"),
    ("NeuraHub", "Neura Hub", "Prevents word merging"),
    ("NeuraChat", "Neura Chat", "Prevents word merging"),
    ("NeuraRAG", "Neura RAG", "Prevents word merging"),
    ("NeuraFlow", "Neura Flow", "Prevents word merging"),
    ("NeuraCrew", "Neura Crew", "Prevents word merging"),
    ("NeuraMCP", "Neura MCP", "Prevents word merging"),
    ("NeuraLLM", "Neura LLM", "Prevents word merging"),
    ("NeuraConnect", "Neura Connect", "Prevents word merging"),
    ("NeuraVision", "Neura Vision", "Prevents word merging"),
    ("workflow", "worke flo", "French pronunciation"),
    ("switch case", "switche case", "English pronunciation"),
]


@dataclass
class Substitution:
    """A single pronunciation substitution."""

    word: str
    replacement: str
    reason: str = ""


def load_substitutions(path: Path | None = None) -> list[Substitution]:
    """Load substitutions from JSON file. Returns builtins if file doesn't exist."""
    target = path or DEFAULT_FILE

    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return [Substitution(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning("Failed to load pronunciation file %s: %s", target, e)

    return [Substitution(w, r, reason) for w, r, reason in BUILTIN_SUBSTITUTIONS]


def save_substitutions(subs: list[Substitution], path: Path | None = None) -> None:
    """Save substitutions to JSON file."""
    target = path or DEFAULT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(s) for s in subs]
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_matches(text: str, subs: list[Substitution]) -> list[tuple[str, str, int, int]]:
    """Find substitution matches in text.

    Returns list of (word, replacement, start, end) tuples.
    """
    matches = []
    for sub in subs:
        if not sub.word:
            continue
        pattern = re.compile(re.escape(sub.word), re.IGNORECASE)
        for m in pattern.finditer(text):
            matches.append((sub.word, sub.replacement, m.start(), m.end()))
    return sorted(matches, key=lambda x: x[2])


def apply_substitutions(text: str, subs: list[Substitution]) -> str:
    """Apply all substitutions to text (case-insensitive)."""
    result = text
    for sub in subs:
        if not sub.word:
            continue
        pattern = re.compile(re.escape(sub.word), re.IGNORECASE)
        result = pattern.sub(sub.replacement, result)
    return result
