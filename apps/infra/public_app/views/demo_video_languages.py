"""Per-language renditions of a demo video, as the player needs them.

The catalog (``VIDEO_CATALOG`` in pages_data.py) stores the English and Japanese
files in flat keys: ``url``/``captions`` for English, ``ja_url``/``ja_captions``
for Japanese. That is enough for two download links and for the Open Graph tags,
but not for a player that switches language without losing the viewer's place: it
needs, per rendition, the video file, its caption file, the UI language shown in
that recording, and a label.

This module turns the catalog entry into that list. A third, optional key
``renditions`` lets a video publish an alternate UI-locale rendition (Japanese
narration over an English UI, for a page that is not translated yet) without
changing the flat keys the rest of the page, the tests and the OG tags use.

Everything here is pure: no Django, no template, so the mapping is unit-testable
and the same list feeds the template, the verification harness and any future
scitex-ui player primitive.
"""

# Labels for the languages the pipeline records; the catalog may also give one.
LANGUAGE_LABELS = {"en": "English", "ja": "日本語"}
DEFAULT_UI_LOCALE = "en"


def rendition_code(language: str, ui_locale: str) -> str:
    """The id a button and a deep link use: ``ja``, or ``ja@en`` for an alternate."""
    if not ui_locale or ui_locale == language:
        return language
    return f"{language}@{ui_locale}"


def _entry(*, language: str, ui_locale: str, url: str, captions: str, label: str = "",
           note: str = "") -> dict:
    return {
        "code": rendition_code(language, ui_locale),
        "language": language,
        "ui_locale": ui_locale,
        "label": label or LANGUAGE_LABELS.get(language, language.upper()),
        "src": url,
        "captions": captions,
        # Captions follow the narration, not the UI: a Japanese-narrated
        # recording over the English UI still shows the Japanese subtitles.
        "captionCode": language,
        "note": note,
        "canonical": ui_locale == language,
    }


def _declared(video: dict) -> list[dict]:
    """Renditions the catalog declares explicitly, in order."""
    declared = video.get("renditions") or []
    entries = []
    for item in declared:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        language = str(item.get("language", ""))
        ui_locale = str(item.get("ui_locale", language))
        entries.append(
            _entry(
                language=language,
                ui_locale=ui_locale,
                url=str(item["url"]),
                captions=str(item.get("captions", "")),
                label=str(item.get("label", "")),
                note=str(item.get("note", "")),
            )
        )
    return entries


def _from_flat_keys(video: dict) -> list[dict]:
    """The two-language shape every published guide uses today."""
    entries = []
    if video.get("url"):
        entries.append(
            _entry(
                language="en",
                ui_locale=str(video.get("url_ui_locale", DEFAULT_UI_LOCALE)),
                url=str(video["url"]),
                captions=str(video.get("captions", "")),
            )
        )
    if video.get("ja_url"):
        entries.append(
            _entry(
                language="ja",
                ui_locale=str(video.get("ja_url_ui_locale", "ja")),
                url=str(video["ja_url"]),
                captions=str(video.get("ja_captions", "")),
            )
        )
    return entries


def languages_for(video: dict) -> list[dict]:
    """Every playable rendition of one catalog entry, in publishing order."""
    entries = _declared(video) or _from_flat_keys(video)
    seen, unique = set(), []
    for entry in entries:
        if entry["code"] in seen:
            continue
        seen.add(entry["code"])
        unique.append(entry)
    return unique


def default_language(entries: list[dict], site_language: str = "en") -> str:
    """The rendition to start on: the visitor's language when the video has it."""
    wanted = (site_language or "en").split("-")[0].lower()
    for entry in entries:
        if entry["language"] == wanted and entry["canonical"]:
            return entry["code"]
    for entry in entries:
        if entry["language"] == wanted:
            return entry["code"]
    return entries[0]["code"] if entries else ""


def default_captions(entries: list[dict], site_language: str = "en") -> str:
    """The caption language to start with, empty when that file does not exist."""
    code = default_language(entries, site_language)
    for entry in entries:
        if entry["code"] == code:
            return entry["captionCode"] if entry["captions"] else ""
    return ""
