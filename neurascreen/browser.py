"""Playwright browser engine: login, navigation, action execution."""

import logging
import random
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Page, BrowserContext, sync_playwright, Playwright

from .config import Config
from .scenario import Scenario, Step

logger = logging.getLogger("videogen")

MAX_CONSECUTIVE_FAILURES = 3


class BrowserEngine:
    """Drives a Playwright browser through scenario steps."""

    def __init__(self, config: Config):
        self.config = config
        self.audio_map: dict[int, Path] = {}
        self.audio_timestamps: list[tuple[float, Path]] = []
        self._recording_start_time: float = 0.0
        self._playwright: Playwright | None = None
        self._browser = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    def start(self) -> Page:
        """Launch browser, optionally fullscreen on a specific screen via CDP."""
        self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(
            headless=self.config.browser_headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context_opts: dict = {
            "locale": "fr-FR",
            "timezone_id": "Europe/Paris",
            "no_viewport": True,
        }

        self._context = self._browser.new_context(**context_opts)
        self._page = self._context.new_page()

        if not self.config.browser_headless and self.config.browser_screen_offset > 0:
            self._move_to_screen_and_fullscreen()

        self._page.add_init_script("""
            const style = document.createElement('style');
            style.textContent = '* { cursor: default !important; }';
            document.head.appendChild(style);
        """)

        return self._page

    def _move_to_screen_and_fullscreen(self) -> None:
        """Position browser window on the target screen and enter fullscreen via CDP."""
        if not self._page or not self._context:
            return

        cdp = self._context.new_cdp_session(self._page)
        target = cdp.send("Browser.getWindowForTarget")
        window_id = target["windowId"]

        screen_offset_x = self.config.browser_screen_offset
        cdp.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {
                "left": screen_offset_x,
                "top": 0,
                "width": 2560,
                "height": 1440,
                "windowState": "normal",
            },
        })
        time.sleep(0.5)

        cdp.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": "fullscreen"},
        })
        time.sleep(1)

        size = self._page.evaluate("() => ({ w: window.innerWidth, h: window.innerHeight })")
        logger.info(f"Browser fullscreen: {size['w']}x{size['h']}")

    def login(self) -> None:
        """Authenticate to the target application."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        if not self.config.app_email or not self.config.app_password:
            logger.info("No credentials configured, skipping login")
            return

        login_url = self.config.login_url
        if login_url.startswith("/"):
            login_url = f"{self.config.app_url}{login_url}"

        logger.info(f"Logging in to {login_url}...")
        self._page.goto(login_url, wait_until="domcontentloaded", timeout=10000)
        self._page.wait_for_timeout(1000)

        self._page.fill("input[name='email'], input[type='email']", self.config.app_email)
        self._page.fill("input[name='password'], input[type='password']", self.config.app_password)
        self._page.click("button[type='submit']")
        self._page.wait_for_timeout(3000)

        current_url = self._page.url
        if "/login" in current_url:
            raise RuntimeError(f"Login failed - still on login page: {current_url}")

        logger.info(f"Login successful - redirected to: {current_url}")

    def execute_scenario(self, scenario: Scenario) -> None:
        """Execute all steps in a scenario."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        logger.info(f"Executing scenario: {scenario.title} ({len(scenario.steps)} steps)")
        consecutive_failures = 0

        for i, step in enumerate(scenario.steps):
            step_label = step.title or f"Step {i + 1}: {step.action}"
            logger.info(f"  [{i + 1}/{len(scenario.steps)}] {step_label}")

            success = self._execute_step(step, i)
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(f"Aborting: {MAX_CONSECUTIVE_FAILURES} consecutive step failures")
                    break

            if step.screenshot_after and self._page:
                screenshot_path = self.config.temp_dir / f"screenshot_{i + 1:03d}.png"
                self._page.screenshot(path=str(screenshot_path))

    def _execute_step(self, step: Step, step_index: int = -1) -> bool:
        """Execute a single step with retry logic."""
        try:
            self._do_step(step, step_index)
            return True
        except Exception as e:
            logger.warning(f"  Step failed: {e}. Retrying in 3s...")
            time.sleep(3)
            try:
                self._do_step(step, step_index)
                return True
            except Exception as e2:
                logger.error(f"  Step failed after retry: {e2}. Skipping.")
                return False

    @staticmethod
    def _play_audio(audio_path: Path) -> subprocess.Popen | None:
        """Play a WAV file in background via afplay (macOS)."""
        if not audio_path or not audio_path.exists():
            return None
        return subprocess.Popen(
            ["afplay", str(audio_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _do_step(self, step: Step, step_index: int = -1) -> None:
        """Execute the actual step action."""
        page = self._page
        if not page:
            raise RuntimeError("No page available")

        selector = step.selector

        time.sleep(random.uniform(0.1, 0.3))

        match step.action:
            case "navigate":
                url = step.url or ""
                if url.startswith("/"):
                    url = f"{self.config.app_url}{url}"
                logger.debug(f"    navigate -> {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)

            case "click":
                if not selector:
                    raise ValueError("click requires a selector")
                page.wait_for_selector(selector, timeout=10000)
                element = page.query_selector(selector)
                if element:
                    box = element.bounding_box()
                    if box:
                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                        time.sleep(random.uniform(0.05, 0.15))
                page.click(selector)

            case "click_text":
                if not step.text:
                    raise ValueError("click_text requires text")
                locator = page.get_by_text(step.text, exact=True)
                locator.wait_for(timeout=10000)
                box = locator.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    time.sleep(random.uniform(0.05, 0.15))
                locator.click()

            case "type":
                if not selector or not step.text:
                    raise ValueError("type requires selector and text")
                page.wait_for_selector(selector, timeout=10000)
                page.click(selector)
                for char in step.text:
                    page.keyboard.type(char)
                    time.sleep(step.delay / 1000)

            case "scroll":
                if not selector:
                    raise ValueError("scroll requires a selector")
                page.wait_for_selector(selector, timeout=10000)
                delta = step.amount if step.direction == "down" else -step.amount
                element = page.query_selector(selector)
                if element:
                    box = element.bounding_box()
                    if box:
                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.mouse.wheel(0, delta)

            case "hover":
                if not selector:
                    raise ValueError("hover requires a selector")
                page.wait_for_selector(selector, timeout=10000)
                page.hover(selector)

            case "key":
                if not step.text:
                    raise ValueError("key requires text (key name)")
                page.keyboard.press(step.text)

            case "wait":
                audio_path = self.audio_map.get(step_index)
                audio_proc = None
                if audio_path:
                    if self._recording_start_time > 0:
                        ts = time.time() - self._recording_start_time
                        self.audio_timestamps.append((ts, audio_path))
                    audio_proc = self._play_audio(audio_path)
                    logger.debug(f"    playing audio: {audio_path.name}")
                time.sleep(step.duration / 1000)
                if audio_proc and audio_proc.poll() is None:
                    audio_proc.wait(timeout=30)

            case "drag":
                if not step.text:
                    raise ValueError("drag requires text (palette item name)")
                palette_items = page.query_selector_all("[draggable='true']")
                target_item = None
                for pi in palette_items:
                    pi_name = pi.inner_text().strip().split("\n")[0]
                    if pi_name.lower() == step.text.lower():
                        target_item = pi
                        break
                if not target_item:
                    raise ValueError(f"Palette item '{step.text}' not found")
                target_item.scroll_into_view_if_needed()
                time.sleep(0.3)
                ibox = target_item.bounding_box()
                if not ibox:
                    raise ValueError(f"Palette item '{step.text}' has no bounding box")
                canvas = page.query_selector(".react-flow")
                if not canvas:
                    raise ValueError("Canvas (.react-flow) not found")
                cbox = canvas.bounding_box()
                if not cbox:
                    raise ValueError("Canvas has no bounding box")
                sx = ibox["x"] + ibox["width"] / 2
                sy = ibox["y"] + ibox["height"] / 2
                dx = cbox["x"] + cbox["width"] * 0.6
                dy = cbox["y"] + cbox["height"] * 0.5
                page.mouse.move(sx, sy)
                time.sleep(0.15)
                page.mouse.down()
                time.sleep(0.15)
                for s in range(15):
                    t = (s + 1) / 15
                    page.mouse.move(sx + (dx - sx) * t, sy + (dy - sy) * t)
                    time.sleep(0.03)
                page.mouse.up()
                time.sleep(1)

            case "delete_node":
                nodes = page.query_selector_all(".react-flow__node")
                if nodes:
                    del_btn = nodes[-1].query_selector('button[title="Supprimer"], button[title="Delete"]')
                    if del_btn:
                        del_btn.click()
                        time.sleep(0.5)

            case "close_modal":
                cancel_btn = page.locator(
                    'div.fixed.inset-0 button:has-text("Annuler"), '
                    'div.fixed.inset-0 button:has-text("Cancel"), '
                    '[role="dialog"] button:has-text("Cancel"), '
                    '[role="dialog"] button:has-text("Close")'
                ).first
                cancel_btn.click(timeout=5000)
                time.sleep(0.8)

            case "zoom_out":
                count = step.amount if step.amount > 0 else 5
                for _ in range(count):
                    page.click('button[title="zoom out"]')
                    time.sleep(0.15)

            case "fit_view":
                page.click('button[title="fit view"]')
                time.sleep(0.8)

            case "screenshot":
                pass

            case _:
                raise ValueError(f"Unknown action: {step.action}")

        if step.wait > 0 and step.action != "wait":
            time.sleep(step.wait / 1000)

    def stop(self) -> None:
        """Close browser and cleanup."""
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")
