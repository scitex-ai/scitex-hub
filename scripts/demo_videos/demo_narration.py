"""Text-to-speech narration clips and per-language narration tracks."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from demo_tools import MediaTools, find_media_tools, media_duration

#: The backends the recorder offers. gTTS needs no key and takes a language code as
#: its voice; ElevenLabs needs a key and takes a voice name or id.
NARRATION_BACKENDS = ("gtts", "elevenlabs")
ELEVENLABS_VOICE_EXAMPLE = "sarah"


class NarrationUnavailable(RuntimeError):
    pass


def voice_for(backend: str, voice: str, language: str) -> str:
    """Which voice a backend should be asked for.

    gTTS is per-language: its "voice" is the language code, so a per-language
    narration is simply the language. ElevenLabs is per-speaker: the same premade
    voice reads any language, so a language code there is not a voice and must not
    be passed as one — the caller has to name the voice, and being explicit is the
    point (the public demos use one chosen voice, Sarah).
    """
    if backend == "elevenlabs":
        if not voice:
            raise NarrationUnavailable(
                f"the elevenlabs backend needs a voice name or id "
                f"(for example --voice {ELEVENLABS_VOICE_EXAMPLE}); a language code is not a voice"
            )
        return voice
    return voice or language


@dataclass(frozen=True)
class NarrationClip:
    path: Path
    duration_seconds: float


def synthesize_clip(text: str, language: str, out_path: Path,
                    tools: MediaTools | None = None, backend: str = "gtts",
                    voice: str = "") -> NarrationClip:
    """Synthesize one line through scitex_audio and report how long it runs."""
    if backend not in NARRATION_BACKENDS:
        raise NarrationUnavailable(
            f"unknown narration backend {backend!r}; expected one of {list(NARRATION_BACKENDS)}"
        )
    try:
        import scitex_audio
    except ImportError as error:
        raise NarrationUnavailable("scitex_audio is not installed") from error
    chosen_voice = voice_for(backend, voice, language)
    try:
        audio = scitex_audio.generate_bytes(text, backend=backend, voice=chosen_voice)
    except Exception as error:
        raise NarrationUnavailable(
            f"{backend} failed for voice {chosen_voice!r}: {error}"
        ) from error
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
