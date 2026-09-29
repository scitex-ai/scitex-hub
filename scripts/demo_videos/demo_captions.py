"""WebVTT captions and plain-text transcripts for the demo-video recorder."""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class TimedCaption:
    text: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class Chapter:
    """A named span of the walkthrough, for the player's chapter track.

    Chapters are what makes an alternate UI-locale rendition usable: the same
    narration drives the same chapters, so a viewer who switches rendition keeps
    the same map of the walkthrough instead of hunting for the step they were on.
    """

    title: str
    start_seconds: float
    end_seconds: float


def format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def build_webvtt(captions: list[TimedCaption]) -> str:
    blocks = ["WEBVTT"]
    spoken = [caption for caption in captions if caption.text]
    for index, caption in enumerate(spoken, start=1):
        timing = (
            f"{format_timestamp(caption.start_seconds)} --> "
            f"{format_timestamp(caption.end_seconds)}"
        )
        blocks.append(f"{index}\n{timing}\n{caption.text}")
    return "\n\n".join(blocks) + "\n"


def build_transcript(title: str, captions: list[TimedCaption],
                     chapters: list[Chapter] | None = None) -> str:
    """The plain-text transcript, with a YouTube-style chapter list when there is one.

    YouTube reads chapters out of the description as `MM:SS Title` lines, which is
    how the upload step in docs/ops/demo-videos.md gets them without retyping.
    """
    spoken = [caption.text for caption in captions if caption.text]
    lines = [title, ""]
    if chapters:
        lines.append("Chapters")
        lines += [f"{chapter_timestamp(chapter.start_seconds)} {chapter.title}"
                  for chapter in chapters]
        lines.append("")
    lines += [f"{index}. {text}" for index, text in enumerate(spoken, 1)]
    return "\n".join(lines) + "\n"


def chapter_timestamp(seconds: float) -> str:
    """`MM:SS` (or `H:MM:SS` past an hour), the form YouTube accepts in a description."""
    total_seconds = int(seconds)
    hours, rest = divmod(total_seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def build_chapter_vtt(chapters: list[Chapter]) -> str:
    """A chapter track: one cue per named span, its text being the chapter title."""
    blocks = ["WEBVTT"]
    for index, chapter in enumerate(chapters, start=1):
        timing = (
            f"{format_timestamp(chapter.start_seconds)} --> "
            f"{format_timestamp(chapter.end_seconds)}"
        )
        blocks.append(f"{index}\n{timing}\n{chapter.title}")
    return "\n\n".join(blocks) + "\n"


def display_width(character: str) -> int:
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


SENTENCE_BREAKS = ("。", "、", ". ", ", ")
CLOSING_PUNCTUATION = {"。", "、", "」", "）"}


def text_width(text: str) -> int:
    return sum(display_width(character) for character in text)


def wrap_caption(text: str, max_width: int) -> str:
    # libass only breaks at spaces, so Japanese lines must be broken here.
    lines, line = [], ""
    for token in tokenize_for_wrapping(text):
        # Japanese punctuation never starts a line, so it may overhang slightly.
        closes_line = token in CLOSING_PUNCTUATION
        if line and not closes_line and text_width(line + token) > max_width:
            head, tail = split_at_sentence_break(line, max_width // 2)
            lines.append(head.rstrip())
            line = tail.lstrip()
        line += token
    if line:
        lines.append(line.rstrip())
    return "\n".join(lines)


def split_at_sentence_break(line: str, min_head_width: int) -> tuple[str, str]:
    cuts = [line.rfind(mark) + len(mark) for mark in SENTENCE_BREAKS if mark in line]
    cut = max(cuts, default=0)
    if cut and cut < len(line) and text_width(line[:cut]) >= min_head_width:
        return line[:cut], line[cut:]
    return line, ""


def tokenize_for_wrapping(text: str) -> list[str]:
    tokens, word = [], ""
    for character in text:
        if display_width(character) == 2:
            if word:
                tokens.append(word)
                word = ""
            tokens.append(character)
        elif character == " ":
            tokens.append(word + " ")
            word = ""
        else:
            word += character
    if word:
        tokens.append(word)
    return tokens
