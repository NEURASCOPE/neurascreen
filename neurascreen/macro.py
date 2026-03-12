"""Macro recorder: capture browser interactions and generate JSON scenarios."""

import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, BrowserContext

logger = logging.getLogger("videogen")

# JavaScript injected into every page to capture user interactions
_CAPTURE_SCRIPT = """
(() => {
    if (window.__neurascreen_recorder) return;
    window.__neurascreen_recorder = true;
    window.__neurascreen_events = window.__neurascreen_events || [];

    document.addEventListener('click', (e) => {
        const el = e.target;
        const text = el.innerText?.trim().split('\\n')[0]?.substring(0, 80) || '';
        const tag = el.tagName.toLowerCase();
        const selector = _buildSelector(el);
        window.__neurascreen_events.push({
            type: 'click',
            timestamp: Date.now(),
            selector: selector,
            text: text,
            tag: tag,
            url: window.location.pathname,
        });
    }, true);

    document.addEventListener('scroll', (e) => {
        // Debounce: only record scroll after 500ms of inactivity
        clearTimeout(window.__neurascreen_scroll_timer);
        window.__neurascreen_scroll_timer = setTimeout(() => {
            window.__neurascreen_events.push({
                type: 'scroll',
                timestamp: Date.now(),
                scrollY: window.scrollY,
                url: window.location.pathname,
            });
        }, 500);
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
            window.__neurascreen_events.push({
                type: 'key',
                timestamp: Date.now(),
                key: e.key,
                url: window.location.pathname,
            });
        }
    }, true);

    function _buildSelector(el) {
        // Try ID first
        if (el.id) return '#' + el.id;

        // Try unique attribute selectors
        for (const attr of ['data-testid', 'name', 'title', 'aria-label']) {
            const val = el.getAttribute(attr);
            if (val) return el.tagName.toLowerCase() + '[' + attr + '="' + val + '"]';
        }

        // Try tag + class
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\\s+/).slice(0, 3).join('.');
            if (classes) {
                const sel = el.tagName.toLowerCase() + '.' + classes;
                if (document.querySelectorAll(sel).length === 1) return sel;
            }
        }

        // Fallback: tag + nth-child
        const parent = el.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            if (siblings.length === 1) return _buildSelector(parent) + ' > ' + el.tagName.toLowerCase();
            const index = siblings.indexOf(el) + 1;
            return _buildSelector(parent) + ' > ' + el.tagName.toLowerCase() + ':nth-child(' + index + ')';
        }

        return el.tagName.toLowerCase();
    }
})();
"""


def record_macro(
    url: str,
    output_path: Path,
    title: str = "Recorded Scenario",
) -> Path:
    """Open a browser, record user interactions, and save as JSON scenario.

    The user interacts with the browser normally. When they close it
    (or press Ctrl+C in the terminal), the recorded events are converted
    to a NeuraScreen JSON scenario.

    Args:
        url: Starting URL to open.
        output_path: Path for the output JSON file.
        title: Title for the generated scenario.

    Returns:
        Path to the generated scenario file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    navigations = []

    logger.info(f"Starting macro recorder at {url}")
    logger.info("Interact with the browser. Close it or press Ctrl+C to stop recording.")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="fr-FR",
            timezone_id="Europe/Paris",
            no_viewport=True,
        )

        page = context.new_page()

        # Track navigations
        def _on_navigation(frame):
            if frame == page.main_frame:
                navigations.append({
                    "type": "navigate",
                    "timestamp": int(time.time() * 1000),
                    "url": urlparse(page.url).path,
                })

        page.on("framenavigated", _on_navigation)

        # Inject capture script on every page load
        page.add_init_script(_CAPTURE_SCRIPT)
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)

        # Inject on current page too
        page.evaluate(_CAPTURE_SCRIPT)

        try:
            # Wait until browser is closed by user
            while True:
                try:
                    # Check if browser is still open
                    page.evaluate("1")
                    time.sleep(0.5)
                except Exception:
                    break
        except KeyboardInterrupt:
            logger.info("Recording stopped by user (Ctrl+C)")

        # Collect events from the page
        try:
            captured = page.evaluate("window.__neurascreen_events || []")
            events.extend(captured)
        except Exception:
            pass

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    # Merge navigations and captured events, sorted by timestamp
    all_events = navigations + events
    all_events.sort(key=lambda e: e.get("timestamp", 0))

    # Convert events to scenario steps
    steps = _events_to_steps(all_events, url)

    scenario = {
        "title": title,
        "description": f"Recorded from {url}",
        "resolution": {"width": 1920, "height": 1080},
        "steps": steps,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenario, f, indent=2, ensure_ascii=False)

    logger.info(f"Scenario saved: {output_path} ({len(steps)} steps)")
    return output_path


def _events_to_steps(events: list[dict], base_url: str) -> list[dict]:
    """Convert raw browser events to NeuraScreen scenario steps."""
    steps = []
    last_url = urlparse(base_url).path
    last_timestamp = 0

    for event in events:
        timestamp = event.get("timestamp", 0)
        event_type = event.get("type", "")

        # Add wait step if significant pause (>2s) between events
        if last_timestamp > 0 and timestamp - last_timestamp > 2000:
            gap_ms = min(timestamp - last_timestamp, 10000)
            steps.append({
                "action": "wait",
                "duration": int(gap_ms),
                "narration": "",
            })

        if event_type == "navigate":
            url_path = event.get("url", "")
            if url_path and url_path != last_url:
                steps.append({
                    "action": "navigate",
                    "url": url_path,
                    "wait": 1500,
                })
                last_url = url_path

        elif event_type == "click":
            text = event.get("text", "")
            selector = event.get("selector", "")

            # Prefer click_text for elements with meaningful text
            if text and len(text) <= 50 and not text.isspace():
                steps.append({
                    "action": "click_text",
                    "text": text,
                    "wait": 1000,
                })
            elif selector:
                steps.append({
                    "action": "click",
                    "selector": selector,
                    "wait": 1000,
                })

        elif event_type == "scroll":
            steps.append({
                "action": "scroll",
                "selector": "body",
                "direction": "down",
                "amount": 400,
                "wait": 500,
            })

        elif event_type == "key":
            key = event.get("key", "")
            if key:
                steps.append({
                    "action": "key",
                    "text": key,
                    "wait": 500,
                })

        last_timestamp = timestamp

    if not steps:
        steps.append({
            "action": "navigate",
            "url": urlparse(base_url).path or "/",
            "wait": 2000,
        })

    return steps
