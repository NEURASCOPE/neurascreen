"""CLI interface for NeuraScreen."""

import json
import subprocess
import sys
import time
from pathlib import Path

import click

from .config import Config
from .scenario import parse_scenario, validate_scenario
from .recorder import Recorder
from .assembler import Assembler
from .subtitles import generate_srt, generate_chapters
from .utils import setup_logger, format_duration


def _collect_narrations(scenario) -> dict[int, str]:
    """Collect narration texts keyed by step index."""
    return {
        i: step.narration
        for i, step in enumerate(scenario.steps)
        if step.narration and step.narration.strip()
    }


def _collect_narrated_titles(scenario) -> list[str]:
    """Collect step titles for narrated steps only."""
    return [
        step.title or f"Section {i + 1}"
        for i, step in enumerate(scenario.steps)
        if step.narration and step.narration.strip()
    ]


def _generate_extras(
    audio_timestamps, scenario, output_stem: Path, srt: bool, chapters: bool
) -> None:
    """Generate SRT and/or chapter files alongside the video."""
    if srt and audio_timestamps:
        narrations = _collect_narrations(scenario)
        srt_path = output_stem.with_suffix(".srt")
        generate_srt(audio_timestamps, narrations, srt_path)

    if chapters and audio_timestamps:
        titles = _collect_narrated_titles(scenario)
        chapters_path = output_stem.with_suffix(".chapters.txt")
        generate_chapters(audio_timestamps, titles, chapters_path)


@click.group()
@click.version_option(package_name="neurascreen")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, headless: bool) -> None:
    """NeuraScreen - Automated screen walkthrough video generator."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["headless"] = headless


@cli.command()
@click.argument("scenario_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output MP4 path")
@click.option("--srt", is_flag=True, help="Generate SRT subtitle file")
@click.option("--chapters", is_flag=True, help="Generate YouTube chapter markers")
@click.pass_context
def run(ctx: click.Context, scenario_path: str, output: str | None, srt: bool, chapters: bool) -> None:
    """Execute a scenario and generate a video (without narration)."""
    config = Config.load()
    if ctx.obj["headless"]:
        config.browser_headless = True

    logger = setup_logger("videogen", config.logs_dir, ctx.obj["verbose"])
    errors = config.validate()
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    start_time = time.time()

    try:
        scenario = parse_scenario(scenario_path)
        logger.info(f"Scenario: {scenario.title} ({len(scenario.steps)} steps)")

        recorder = Recorder(config)
        raw_video, audio_timestamps = recorder.record(scenario)

        if not raw_video or not raw_video.exists():
            logger.error("No video file produced")
            sys.exit(1)

        assembler = Assembler(config)
        mp4_path = assembler.convert_to_mp4(
            input_path=raw_video,
            output_name=scenario.title,
            output_path=Path(output) if output else None,
        )
        assembler.cleanup_temp()

        _generate_extras(audio_timestamps, scenario, mp4_path, srt, chapters)

        elapsed = time.time() - start_time
        logger.info(f"Done in {format_duration(int(elapsed * 1000))}. Output: {mp4_path}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("scenario_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output MP4 path")
@click.option("--srt", is_flag=True, help="Generate SRT subtitle file")
@click.option("--chapters", is_flag=True, help="Generate YouTube chapter markers")
@click.pass_context
def full(ctx: click.Context, scenario_path: str, output: str | None, srt: bool, chapters: bool) -> None:
    """Execute a scenario with TTS narration and generate a video."""
    config = Config.load()
    if ctx.obj["headless"]:
        config.browser_headless = True

    logger = setup_logger("videogen", config.logs_dir, ctx.obj["verbose"])
    errors = config.validate_tts()
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    start_time = time.time()

    try:
        from .narrator import Narrator

        scenario = parse_scenario(scenario_path)
        logger.info(f"Scenario: {scenario.title} ({len(scenario.steps)} steps)")

        narrator = Narrator(config)
        scenario, audio_map = narrator.prepare_narration(scenario)

        recorder = Recorder(config)
        raw_video, audio_timestamps = recorder.record(scenario, audio_map=audio_map)

        if not raw_video or not raw_video.exists():
            logger.error("No video file produced")
            sys.exit(1)

        assembler = Assembler(config)
        final_name = Path(scenario_path).stem + ".mp4"
        final_path = Path(output) if output else config.output_dir / final_name

        if audio_timestamps:
            video_duration = assembler.get_video_duration(raw_video)
            narration_wav = assembler.build_audio_from_timestamps(audio_timestamps, video_duration)
            temp_mp4 = config.temp_dir / "video_only.mp4"
            assembler.convert_to_mp4(raw_video, output_path=temp_mp4)
            assembler.assemble_with_audio(temp_mp4, narration_wav, final_path)
        else:
            final_path = assembler.convert_to_mp4(
                raw_video, output_name=scenario.title,
                output_path=Path(output) if output else None,
            )

        assembler.cleanup_temp()

        _generate_extras(audio_timestamps, scenario, final_path, srt, chapters)

        elapsed = time.time() - start_time
        logger.info(f"Done in {format_duration(int(elapsed * 1000))}. Output: {final_path}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("scenario_path", type=click.Path(exists=True))
@click.pass_context
def preview(ctx: click.Context, scenario_path: str) -> None:
    """Execute a scenario without recording (for testing)."""
    config = Config.load()
    if ctx.obj["headless"]:
        config.browser_headless = True

    logger = setup_logger("videogen", config.logs_dir, ctx.obj["verbose"])

    try:
        scenario = parse_scenario(scenario_path)
        logger.info(f"Preview: {scenario.title} ({len(scenario.steps)} steps)")

        recorder = Recorder(config)
        recorder.preview(scenario)
        logger.info("Preview complete")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


@cli.command("batch")
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False))
@click.option("--srt", is_flag=True, help="Generate SRT subtitle files")
@click.option("--chapters", is_flag=True, help="Generate YouTube chapter markers")
@click.option("--narration/--no-narration", default=True, help="Enable TTS narration (default: on)")
@click.pass_context
def batch(ctx: click.Context, folder_path: str, srt: bool, chapters: bool, narration: bool) -> None:
    """Generate videos from all scenarios in a folder."""
    config = Config.load()
    if ctx.obj["headless"]:
        config.browser_headless = True

    logger = setup_logger("videogen", config.logs_dir, ctx.obj["verbose"])

    if narration:
        errors = config.validate_tts()
    else:
        errors = config.validate()
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    folder = Path(folder_path)
    scenario_files = sorted(folder.rglob("*.json"))

    if not scenario_files:
        click.echo(f"No scenario files found in {folder}")
        sys.exit(1)

    # Validate all scenarios first
    valid_files = []
    for sf in scenario_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
            errs = validate_scenario(data)
            if errs:
                logger.warning(f"Skipping {sf.name}: {len(errs)} validation errors")
                for e in errs:
                    logger.warning(f"  - {e}")
            else:
                valid_files.append(sf)
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping {sf.name}: invalid JSON ({e})")

    if not valid_files:
        click.echo("No valid scenarios found")
        sys.exit(1)

    click.echo(f"Batch: {len(valid_files)} scenarios to process\n")

    results: list[tuple[str, str, str]] = []  # (name, status, detail)
    batch_start = time.time()

    for i, sf in enumerate(valid_files, 1):
        click.echo(f"[{i}/{len(valid_files)}] {sf.name}")
        scenario_start = time.time()

        try:
            scenario = parse_scenario(str(sf))

            if narration:
                from .narrator import Narrator
                narrator_inst = Narrator(config)
                scenario, audio_map = narrator_inst.prepare_narration(scenario)
            else:
                audio_map = None

            recorder = Recorder(config)
            raw_video, audio_timestamps = recorder.record(
                scenario, audio_map=audio_map if audio_map else None
            )

            if not raw_video or not raw_video.exists():
                results.append((sf.name, "FAIL", "No video produced"))
                continue

            assembler = Assembler(config)
            final_name = sf.stem + ".mp4"
            final_path = config.output_dir / final_name

            if narration and audio_timestamps:
                video_duration = assembler.get_video_duration(raw_video)
                narration_wav = assembler.build_audio_from_timestamps(
                    audio_timestamps, video_duration
                )
                temp_mp4 = config.temp_dir / "video_only.mp4"
                assembler.convert_to_mp4(raw_video, output_path=temp_mp4)
                assembler.assemble_with_audio(temp_mp4, narration_wav, final_path)
            else:
                final_path = assembler.convert_to_mp4(
                    raw_video, output_name=scenario.title
                )

            assembler.cleanup_temp()

            _generate_extras(audio_timestamps, scenario, final_path, srt, chapters)

            elapsed = time.time() - scenario_start
            size_mb = final_path.stat().st_size / (1024 * 1024)
            results.append((sf.name, "OK", f"{size_mb:.1f} MB in {format_duration(int(elapsed * 1000))}"))

        except KeyboardInterrupt:
            logger.info("Batch interrupted by user")
            results.append((sf.name, "SKIP", "Interrupted"))
            break
        except Exception as e:
            logger.error(f"  Failed: {e}")
            results.append((sf.name, "FAIL", str(e)[:80]))

    # Summary
    batch_elapsed = time.time() - batch_start
    click.echo(f"\n{'='*60}")
    click.echo(f"Batch complete: {len(results)}/{len(valid_files)} processed in {format_duration(int(batch_elapsed * 1000))}\n")
    for name, status, detail in results:
        icon = "+" if status == "OK" else "-" if status == "FAIL" else "~"
        click.echo(f"  [{icon}] {name:<40} {detail}")

    failed = sum(1 for _, s, _ in results if s == "FAIL")
    if failed:
        click.echo(f"\n{failed} failed")
        sys.exit(1)


@cli.command("list")
def list_scenarios() -> None:
    """List available scenarios."""
    config = Config.load()
    scenarios_dir = config.scenarios_dir
    if not scenarios_dir.exists():
        click.echo("No scenarios directory found")
        return

    json_files = sorted(scenarios_dir.rglob("*.json"))
    if not json_files:
        click.echo("No scenarios found")
        return

    click.echo(f"Available scenarios ({len(json_files)}):\n")
    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            title = data.get("title", "Untitled")
            steps = len(data.get("steps", []))
            rel = f.relative_to(scenarios_dir)
            click.echo(f"  {str(rel):<40} {title} ({steps} steps)")
        except (json.JSONDecodeError, KeyError):
            click.echo(f"  {f.name:<40} [invalid JSON]")


@cli.command()
@click.argument("scenario_path", type=click.Path(exists=True))
def validate(scenario_path: str) -> None:
    """Validate a scenario JSON file."""
    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    errors = validate_scenario(data)
    if errors:
        click.echo(f"Validation failed ({len(errors)} errors):", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        sys.exit(1)

    steps = len(data.get("steps", []))
    click.echo(f"Valid scenario: {data.get('title', 'Untitled')} ({steps} steps)")


def main() -> None:
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
