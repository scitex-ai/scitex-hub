"""Text-to-speech narration clips and per-language narration tracks."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from demo_tools import MediaTools, find_media_tools, media_duration


class NarrationUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class NarrationClip:
    path: Path
    duration_seconds: float


def synthesize_clip(text: str, language: str, out_path: Path,
                    tools: MediaTools | None = None) -> NarrationClip:
    try:
        import scitex_audio
    except ImportError as error:
        raise NarrationUnavailable("scitex_audio is not installed") from error
    # gTTS is the backend available without API keys; it needs internet access.
    try:
        audio = scitex_audio.generate_bytes(text, backend="gtts", voice=language)
    except Exception as error:
        raise NarrationUnavailable(f"gTTS failed for '{language}': {error}") from error
    out_path.write_bytes(audio)
    return NarrationClip(out_path, media_duration(out_path, tools or find_media_tools()))


def build_narration_track(placed_clips: list[tuple[Path, float]], total_seconds: float,
                          out_path: Path, ffmpeg: str = "ffmpeg") -> None:
    inputs, filters, labels = [], [], []
    for index, (clip_path, start_seconds) in enumerate(placed_clips):
        inputs += ["-i", str(clip_path)]
        delay_ms = round(start_seconds * 1000)
        filters.append(f"[{index}:a]aresample=44100,adelay={delay_ms}|{delay_ms}[a{index}]")
        labels.append(f"[a{index}]")
    mix = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad[out]"
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(filters + [mix]), "-map", "[out]",
         "-t", f"{total_seconds:.3f}", "-c:a", "aac", "-b:a", "128k", str(out_path)],
        check=True,
    )
