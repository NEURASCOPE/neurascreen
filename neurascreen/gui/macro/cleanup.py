"""Post-recording cleanup: dedup clicks, merge navigations, adjust waits."""


def dedup_clicks(events: list[dict], threshold_ms: int = 300) -> list[dict]:
    """Remove duplicate clicks on the same target within threshold_ms.

    Two consecutive click events on the same selector/text within the threshold
    are considered duplicates — only the first is kept.
    """
    if not events:
        return []

    result = [events[0]]
    for event in events[1:]:
        prev = result[-1]
        if (
            event.get("type") == "click"
            and prev.get("type") == "click"
            and _same_target(prev, event)
            and event.get("timestamp", 0) - prev.get("timestamp", 0) < threshold_ms
        ):
            continue
        result.append(event)
    return result


def merge_navigations(events: list[dict]) -> list[dict]:
    """Merge consecutive navigation events, keeping only the last URL."""
    if not events:
        return []

    result = [events[0]]
    for event in events[1:]:
        prev = result[-1]
        if event.get("type") == "navigate" and prev.get("type") == "navigate":
            result[-1] = event
        else:
            result.append(event)
    return result


def cap_waits(events: list[dict], max_ms: int = 5000, min_ms: int = 500) -> list[dict]:
    """Cap wait durations and remove waits shorter than min_ms.

    This operates on raw events (adjusting timestamp gaps) and on
    converted steps (adjusting duration fields).
    """
    if not events:
        return []

    result = []
    for event in events:
        if event.get("type") == "wait" or event.get("action") == "wait":
            duration = event.get("duration", 0)
            if duration < min_ms:
                continue
            if duration > max_ms:
                event = {**event, "duration": max_ms}
        result.append(event)
    return result


def cleanup_events(
    events: list[dict],
    *,
    dedup_threshold_ms: int = 300,
    max_wait_ms: int = 5000,
    min_wait_ms: int = 500,
) -> list[dict]:
    """Apply all cleanup passes to raw events."""
    events = dedup_clicks(events, dedup_threshold_ms)
    events = merge_navigations(events)
    return events


def cleanup_steps(
    steps: list[dict],
    *,
    max_wait_ms: int = 5000,
    min_wait_ms: int = 500,
) -> list[dict]:
    """Apply cleanup to converted scenario steps."""
    return cap_waits(steps, max_ms=max_wait_ms, min_ms=min_wait_ms)


def _same_target(a: dict, b: dict) -> bool:
    """Check if two click events target the same element."""
    # Compare by text first (more reliable than generated selectors)
    text_a = a.get("text", "")
    text_b = b.get("text", "")
    if text_a and text_b:
        return text_a == text_b

    # Fall back to selector comparison
    sel_a = a.get("selector", "")
    sel_b = b.get("selector", "")
    if sel_a and sel_b:
        return sel_a == sel_b

    return False
