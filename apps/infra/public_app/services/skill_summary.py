"""Plain display summaries of leaf skill descriptions; raw metadata is retained."""

import re

_MARKER = re.compile(r"\[(WHAT|WHEN|HOW|TOPIC|DETAILS)\](?=\s|$)")


def skill_description_summary(description):
    """Read the introductory WHAT or TOPIC/DETAILS text, without rendering HTML.

    Only descriptions starting with a recognized structured marker are split.
    Plain text, Markdown links and unknown bracket labels are preserved. Full
    setup/use instructions remain in the original metadata and linked guide.
    Empty YAML scalar indicators are not descriptions. Output remains ordinary
    text and must use the template's normal escaping, never mark_safe.
    """
    if not isinstance(description, str):
        return ""
    text = " ".join(description.split())
    if text in {"", "|", ">", "|-", ">-", "|+", ">+"}:
        return ""
    markers = list(_MARKER.finditer(text))
    if not markers or markers[0].start() != 0:
        return text
    sections = []
    for position, marker in enumerate(markers):
        end = markers[position + 1].start() if position + 1 < len(markers) else len(text)
        sections.append((marker.group(1), text[marker.end():end].strip()))
    first = sections[0][0]
    if first == "TOPIC":
        return " — ".join(value for label, value in sections if label in {"TOPIC", "DETAILS"} and value)
    return sections[0][1]
