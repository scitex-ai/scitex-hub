"""Locate the ffmpeg/ffprobe the renderer needs, and read media durations.

The render script used to call `shutil.which("ffmpeg")` and `ffprobe` directly,
which made it work only inside the dev container. Two things break that:

* the Playwright browser bundle ships a stripped ffmpeg (libvpx only, no
  libx264/aac), so a machine that "has ffmpeg" on PATH through Playwright still
  cannot encode the mp4 or the voice track;
* ffprobe is often absent where ffmpeg is present (Playwright ships only
  `ffmpeg-linux`; the static imageio-ffmpeg build ships only the encoder).

So the renderer resolves both tools here, records which one it used in the
manifest, and reads durations through ffprobe when available and by parsing
`ffmpeg -i` output when it is not.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

FFMPEG_ENV = "SCITEX_DEMO_FFMPEG"
FFPROBE_ENV = "SCITEX_DEMO_FFPROBE"
FONTS_ENV = "SCITEX_DEMO_FONTS_DIR"
# H.264 and AAC are the two encoders the published files need; a build without
# them (Playwright's) can record webm but cannot produce the published mp4.
REQUIRED_ENCODERS = ("libx264", "aac", "libvpx")
_FFMPEG_DURATION = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")


@dataclass(frozen=True)
class MediaTools:
    """The media binaries a render will use, and where they came from."""

    ffmpeg: str
    ffprobe: str
    source: str

    @property
    def has_ffmpeg(self) -> bool:
        return bool(self.ffmpeg)

    @property
    def has_ffprobe(self) -> bool:
        return bool(self.ffprobe)


def _first_usable(candidates) -> str:
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return ""


def _imageio_ffmpeg() -> str:
    """The static ffmpeg bundled with the `imageio-ffmpeg` wheel, if installed."""
    try:
        import imageio_ffmpeg
    except ImportError:
        return ""
    try:
        return _first_usable([imageio_ffmpeg.get_ffmpeg_exe()])
    except Exception:
        return ""


def find_media_tools() -> MediaTools:
    env_ffmpeg = os.environ.get(FFMPEG_ENV, "")
    env_ffprobe = os.environ.get(FFPROBE_ENV, "")
    on_path = shutil.which("ffmpeg") or ""
    if env_ffmpeg:
        ffmpeg, source = _first_usable([env_ffmpeg]), f"environment {FFMPEG_ENV}"
    elif on_path:
        ffmpeg, source = on_path, "PATH"
    else:
        bundled = _imageio_ffmpeg()
        ffmpeg, source = bundled, ("imageio-ffmpeg wheel" if bundled else "missing")
    ffprobe = _first_usable([env_ffprobe, shutil.which("ffprobe") or ""])
    return MediaTools(ffmpeg=ffmpeg, ffprobe=ffprobe, source=source)


def encoder_support(ffmpeg: str) -> list[str]:
    """Which of REQUIRED_ENCODERS this build provides."""
    if not ffmpeg:
        return []
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, check=False
    )
    listed = result.stdout
    return [name for name in REQUIRED_ENCODERS if re.search(rf"\b{name}\b", listed)]


def ffmpeg_version(ffmpeg: str) -> str:
    if not ffmpeg:
        return ""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-version"], capture_output=True, text=True, check=False
    )
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    return first_line.replace("ffmpeg version ", "").split(" Copyright")[0].strip()


def ffprobe_version(ffprobe: str) -> str:
    if not ffprobe:
        return ""
    result = subprocess.run(
        [ffprobe, "-hide_banner", "-version"], capture_output=True, text=True, check=False
    )
    return result.stdout.splitlines()[0] if result.stdout else ""


def duration_from_ffmpeg(ffmpeg: str, path: Path) -> float:
    """Read a container duration out of `ffmpeg -i`, which prints it and exits 1."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, check=False
    )
    match = _FFMPEG_DURATION.search(result.stderr or "")
    if not match:
        raise RuntimeError(f"no duration in ffmpeg output for {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def media_duration(path: Path, tools: MediaTools) -> float:
    """Duration in seconds, by ffprobe when present and `ffmpeg -i` when not."""
    path = Path(path)
    if tools.ffprobe:
        result = subprocess.run(
            [tools.ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    if tools.ffmpeg:
        return duration_from_ffmpeg(tools.ffmpeg, path)
    raise RuntimeError(f"no ffprobe or ffmpeg available to read the duration of {path}")


def font_search_dirs() -> list[str]:
    """Directories libass should look in for the caption font."""
    dirs = []
    extra = os.environ.get(FONTS_ENV, "")
    if extra:
        dirs.extend(part for part in extra.split(os.pathsep) if part)
    for candidate in ("/usr/share/fonts", "/usr/local/share/fonts"):
        if Path(candidate).is_dir():
            dirs.append(candidate)
    return dirs


def installed_font_families() -> list[str]:
    """Font families fontconfig knows, lowercased; empty when fc-list is absent."""
    if not shutil.which("fc-list"):
        return []
    result = subprocess.run(["fc-list"], capture_output=True, text=True, check=False)
    families = set()
    for line in result.stdout.splitlines():
        # `/path/font.ttf: Family One,Family Two:style=Regular`
        fields = line.split(":")
        if len(fields) < 2:
            continue
        for family in fields[1].split(","):
            cleaned = family.strip().lower()
            if cleaned:
                families.add(cleaned)
    return sorted(families)


def caption_font_available(family: str, extra_dirs: list[str] | None = None) -> bool:
    """Whether libass can render `family`, so a missing CJK font is a loud skip.

    ``extra_dirs`` are the directories passed to libass as ``fontsdir`` (a checked
    out font in the workspace is enough for the render even when fontconfig has
    never seen it), and a fontconfig that is not installed at all cannot answer
    either way, so the check says nothing rather than something wrong.
    """
    for directory in extra_dirs or []:
        folder = Path(directory)
        if not folder.is_dir():
            continue
        for path in folder.glob("*.tt[fc]"):
            if family.lower().replace(" ", "") in path.stem.lower().replace(" ", ""):
                return True
    known = installed_font_families()
    if not known:
        # fontconfig missing: libass will fall back silently, do not claim either way.
        return True
    needle = family.lower()
    return any(needle in entry for entry in known)
