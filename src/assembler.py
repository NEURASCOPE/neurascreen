"""Video assembler: crop/scale + audio assembly via ffmpeg."""

import logging
import shutil
import subprocess
from pathlib import Path

from .config import Config
from .utils import slugify

logger = logging.getLogger("videogen")


class Assembler:
    """Processes raw screen captures into YouTube-ready MP4."""

    def __init__(self, config: Config):
        self.config = config
        self._check_ffmpeg()

    @staticmethod
    def get_video_duration(path: Path) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            val = result.stdout.strip()
            if val and val != "N/A":
                return float(val)

        # Fallback: estimate from file size (~4 Mbps)
        size_bytes = path.stat().st_size
        return size_bytes / (4_000_000 / 8)

    @staticmethod
    def _check_ffmpeg() -> None:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found. Install it: brew install ffmpeg")

    def convert_to_mp4(
        self,
        input_path: Path,
        output_name: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """Process raw screen capture to YouTube-ready MP4."""
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        if output_path is None:
            name = slugify(output_name) if output_name else input_path.stem
            output_path = self.config.output_dir / f"{name}.mp4"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Processing {input_path.name} -> {output_path.name}")

        # Probe input resolution
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(input_path),
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        input_w, input_h = 0, 0
        if probe_result.returncode == 0 and probe_result.stdout.strip():
            parts = probe_result.stdout.strip().split(",")
            if len(parts) == 2:
                input_w, input_h = int(parts[0]), int(parts[1])

        target_w = self.config.video_width
        target_h = self.config.video_height

        vf_parts = []
        if input_w > 0 and input_h > 0 and (input_w != target_w or input_h != target_h):
            crop_w = min(input_w, int(input_h * target_w / target_h))
            crop_h = min(input_h, int(input_w * target_h / target_w))
            vf_parts.append(f"crop={crop_w}:{crop_h}:0:0")
            vf_parts.append(f"scale={target_w}:{target_h}")
            logger.info(f"  Input: {input_w}x{input_h} -> crop {crop_w}x{crop_h} -> scale {target_w}x{target_h}")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-f", "lavfi",
            "-i", "anullsrc=r=48000:cl=stereo",
        ]
        cmd += ["-c:v", "libx264"]
        if vf_parts:
            cmd += ["-vf", ",".join(vf_parts)]
        cmd += [
            "-preset", "slow",
            "-crf", "18",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-r", str(self.config.video_fps),
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"ffmpeg error:\n{result.stderr[-500:]}")
            raise RuntimeError(f"ffmpeg conversion failed (exit code {result.returncode})")

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Output: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def assemble_with_audio(self, video_path: Path, audio_path: Path, output_path: Path) -> Path:
        """Assemble video with audio narration track."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Assembling video + audio -> {output_path.name}")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-movflags", "+faststart",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"ffmpeg error:\n{result.stderr[-500:]}")
            raise RuntimeError(f"ffmpeg assembly failed (exit code {result.returncode})")

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Final output: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def build_audio_from_timestamps(
        self,
        audio_timestamps: list[tuple[float, Path]],
        total_duration_s: float,
        output_path: Path | None = None,
    ) -> Path:
        """Build a narration audio track from real timestamps."""
        if output_path is None:
            output_path = self.config.temp_dir / "narration_synced.wav"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not audio_timestamps:
            self._create_silence(output_path, total_duration_s)
            return output_path

        audio_dir = self.config.temp_dir / "audio_sync"
        audio_dir.mkdir(parents=True, exist_ok=True)

        segment_files: list[Path] = []
        prev_end_s = 0.0

        for idx, (start_s, audio_path) in enumerate(audio_timestamps):
            gap_s = start_s - prev_end_s
            if gap_s > 0.01:
                silence_path = audio_dir / f"silence_{idx}.wav"
                self._create_silence(silence_path, gap_s)
                segment_files.append(silence_path)

            segment_files.append(audio_path)
            duration_s = self._get_wav_duration_s(audio_path)
            prev_end_s = start_s + duration_s

        trailing_s = total_duration_s - prev_end_s
        if trailing_s > 0.01:
            silence_path = audio_dir / "silence_trailing.wav"
            self._create_silence(silence_path, trailing_s)
            segment_files.append(silence_path)

        concat_list = audio_dir / "concat.txt"
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-ac", "1", "-ar", "48000",
            "-c:a", "pcm_s16le",
            str(output_path),
        ]

        logger.info(f"Building synced audio from {len(audio_timestamps)} timestamps...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build synced narration audio:\n{result.stderr[-500:]}")

        size_kb = output_path.stat().st_size / 1024
        logger.info(f"Synced narration: {total_duration_s:.1f}s, {size_kb:.0f} KB")
        return output_path

    @staticmethod
    def _create_silence(path: Path, duration_s: float) -> None:
        duration_s = max(duration_s, 0.01)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono",
            "-t", f"{duration_s:.3f}",
            "-c:a", "pcm_s16le",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create silence: {result.stderr[-200:]}")

    @staticmethod
    def _get_wav_duration_s(path: Path) -> float:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            try:
                return float(result.stdout.strip())
            except ValueError:
                pass
        return path.stat().st_size / 96000

    def cleanup_temp(self) -> None:
        """Remove temporary video files."""
        for subdir in ["video", "audio_sync"]:
            d = self.config.temp_dir / subdir
            if d.exists():
                for f in d.iterdir():
                    f.unlink()
