"""WebVTT captions and plain-text transcripts for the demo-video recorder."""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class TimedCaption:
    text: str
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


def build_transcript(title: str, captions: list[TimedCaption]) -> str:
    spoken = [caption.text for caption in captions if caption.text]
    lines = [title, ""] + [f"{index}. {text}" for index, text in enumerate(spoken, 1)]
    return "\n".join(lines) + "\n"


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
