"""Scenario parser and validator."""

import json
from dataclasses import dataclass
from pathlib import Path


VALID_ACTIONS = {
    "navigate", "click", "click_text", "type", "scroll", "hover",
    "wait", "screenshot", "drag", "delete_node", "close_modal",
    "zoom_out", "fit_view", "key",
}
VALID_SCROLL_DIRECTIONS = {"up", "down"}


@dataclass
class Step:
    """A single step in a scenario."""

    title: str
    action: str
    selector: str | None = None
    url: str | None = None
    text: str | None = None
    delay: int = 50
    direction: str | None = None
    amount: int = 300
    duration: int = 1000
    wait: int = 1000
    narration: str = ""
    screenshot_after: bool = False
    highlight: str | None = None


@dataclass
class Scenario:
    """A complete demo scenario."""

    title: str
    description: str
    resolution: dict[str, int]
    steps: list[Step]
    source_path: str = ""

    @property
    def width(self) -> int:
        return self.resolution.get("width", 1920)

    @property
    def height(self) -> int:
        return self.resolution.get("height", 1080)


def validate_scenario(data: dict) -> list[str]:
    """Validate scenario JSON structure. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        return ["Scenario must be a JSON object"]

    if "title" not in data or not data["title"]:
        errors.append("Missing required field: title")

    if "steps" not in data or not isinstance(data.get("steps"), list):
        errors.append("Missing or invalid field: steps (must be a list)")
        return errors

    if len(data["steps"]) == 0:
        errors.append("Scenario must have at least one step")

    for i, step in enumerate(data.get("steps", [])):
        prefix = f"Step {i + 1}"

        if not isinstance(step, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        action = step.get("action")
        if not action:
            errors.append(f"{prefix}: missing required field 'action'")
            continue

        if action not in VALID_ACTIONS:
            errors.append(f"{prefix}: invalid action '{action}'. Valid: {sorted(VALID_ACTIONS)}")
            continue

        if action == "navigate" and not step.get("url"):
            errors.append(f"{prefix}: 'navigate' requires 'url'")

        if action in ("click", "type", "hover") and not step.get("selector"):
            errors.append(f"{prefix}: '{action}' requires 'selector'")

        if action == "click_text" and not step.get("text"):
            errors.append(f"{prefix}: 'click_text' requires 'text'")

        if action == "type" and not step.get("text"):
            errors.append(f"{prefix}: 'type' requires 'text'")

        if action == "scroll":
            if not step.get("selector"):
                errors.append(f"{prefix}: 'scroll' requires 'selector'")
            direction = step.get("direction", "down")
            if direction not in VALID_SCROLL_DIRECTIONS:
                errors.append(f"{prefix}: invalid scroll direction '{direction}'")

        if action == "drag" and not step.get("text"):
            errors.append(f"{prefix}: 'drag' requires 'text' (item name)")

    return errors


def parse_scenario(path: str | Path) -> Scenario:
    """Parse and validate a scenario JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = validate_scenario(data)
    if errors:
        raise ValueError(f"Invalid scenario ({path}):\n" + "\n".join(f"  - {e}" for e in errors))

    steps = []
    for step_data in data["steps"]:
        steps.append(Step(
            title=step_data.get("title", ""),
            action=step_data["action"],
            selector=step_data.get("selector"),
            url=step_data.get("url"),
            text=step_data.get("text"),
            delay=step_data.get("delay", 50),
            direction=step_data.get("direction"),
            amount=step_data.get("amount", 300),
            duration=step_data.get("duration", 1000),
            wait=step_data.get("wait", 1000),
            narration=step_data.get("narration", ""),
            screenshot_after=step_data.get("screenshot_after", False),
            highlight=step_data.get("highlight"),
        ))

    return Scenario(
        title=data["title"],
        description=data.get("description", ""),
        resolution=data.get("resolution", {"width": 1920, "height": 1080}),
        steps=steps,
        source_path=str(path),
    )
