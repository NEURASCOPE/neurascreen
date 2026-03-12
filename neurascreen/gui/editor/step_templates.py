"""Pre-built step templates for common patterns."""

TEMPLATES: dict[str, list[dict]] = {
    "Navigation + Narration": [
        {"action": "navigate", "url": "/page", "wait": 2000},
        {"action": "wait", "duration": 1000, "narration": "Description of the page."},
    ],
    "Click + Narration": [
        {"action": "click_text", "text": "Button Text", "wait": 1500},
        {"action": "wait", "duration": 1000, "narration": "Description of what happened."},
    ],
    "Form Fill": [
        {"action": "click", "selector": "input[name='field']", "wait": 300},
        {"action": "type", "selector": "input[name='field']", "text": "Value", "wait": 500},
        {"action": "wait", "duration": 1000, "narration": "We filled in the field."},
    ],
    "Drag + Configure + Delete": [
        {"action": "drag", "text": "Node Name", "wait": 300},
        {"action": "fit_view", "wait": 300},
        {"action": "zoom_out", "amount": 4, "wait": 300},
        {"action": "click", "selector": ".react-flow__node button[title='Configurer']", "wait": 1500},
        {"action": "wait", "duration": 1000, "narration": "Description of the node configuration."},
        {"action": "close_modal", "wait": 300},
        {"action": "delete_node", "wait": 300},
    ],
    "Scroll Down + Narration": [
        {"action": "scroll", "selector": "main", "direction": "down", "amount": 400, "wait": 1000},
        {"action": "wait", "duration": 1000, "narration": "More content is visible below."},
    ],
    "Introduction": [
        {"title": "Introduction", "action": "wait", "duration": 1000, "narration": "Welcome to this demo."},
    ],
    "Conclusion": [
        {"title": "Conclusion", "action": "wait", "duration": 1000, "narration": "That wraps up this demo."},
    ],
}


def get_template_names() -> list[str]:
    """Return sorted list of template names."""
    return list(TEMPLATES.keys())


def get_template_steps(name: str) -> list[dict]:
    """Return a deep copy of template steps."""
    import copy
    steps = TEMPLATES.get(name, [])
    return copy.deepcopy(steps)
