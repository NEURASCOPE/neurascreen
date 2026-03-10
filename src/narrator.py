"""Narration orchestrator: text -> audio -> timing synchronization."""

import logging
from pathlib import Path

from .config import Config
from .scenario import Scenario, Step
from .tts import create_tts_client, get_wav_duration_ms

logger = logging.getLogger("videogen")

NARRATION_PADDING_MS = 500


class Narrator:
    """Orchestrates narration generation and timing synchronization."""

    def __init__(self, config: Config):
        self.config = config
        self.tts = create_tts_client(config)

    def prepare_narration(self, scenario: Scenario) -> tuple[Scenario, dict[int, Path]]:
        """Generate all narration audio and adjust scenario timing.

        Returns:
            Tuple of (adjusted_scenario, audio_map) where audio_map is {step_index: wav_path}.
        """
        narrations = []
        for i, step in enumerate(scenario.steps):
            if step.narration and step.narration.strip():
                narrations.append((i, step.narration))

        if not narrations:
            logger.info("No narration in this scenario")
            return scenario, {}

        logger.info(f"Generating narration for {len(narrations)} steps...")

        audio_map = self.tts.generate_all(narrations)

        duration_map: dict[int, int] = {}
        for step_idx, audio_path in audio_map.items():
            duration_map[step_idx] = get_wav_duration_ms(audio_path)

        adjusted_steps = []
        for i, step in enumerate(scenario.steps):
            new_step = Step(
                title=step.title,
                action=step.action,
                selector=step.selector,
                url=step.url,
                text=step.text,
                delay=step.delay,
                direction=step.direction,
                amount=step.amount,
                duration=step.duration,
                wait=step.wait,
                narration=step.narration,
                screenshot_after=step.screenshot_after,
                highlight=step.highlight,
            )

            if i in duration_map:
                audio_duration = duration_map[i]
                required_wait = audio_duration + NARRATION_PADDING_MS
                if new_step.wait < required_wait:
                    logger.debug(
                        f"  Step {i + 1}: extending wait {new_step.wait}ms -> {required_wait}ms "
                        f"(audio: {audio_duration}ms)"
                    )
                    new_step.wait = required_wait
                if new_step.action == "wait" and new_step.duration < required_wait:
                    new_step.duration = required_wait

            adjusted_steps.append(new_step)

        adjusted_scenario = Scenario(
            title=scenario.title,
            description=scenario.description,
            resolution=scenario.resolution,
            steps=adjusted_steps,
            source_path=scenario.source_path,
        )

        return adjusted_scenario, audio_map
