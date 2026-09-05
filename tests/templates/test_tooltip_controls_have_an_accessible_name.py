"""Every element that carries data-tooltip must have an accessible name.

Found 2026-09-03 by scitex-ui in their own standalone_shell.html and, byte for
byte, in hub's workspace_viewer_pane.html: an icon-only <button> with
data-tooltip="Supported formats: ..." and title="" — the empty title was set on
purpose (it suppresses the native tooltip) and it also removed the button's only
accessible name. A screen reader announced "button" and stopped; the tooltip's
content, the control's whole point, was unreachable.

The parser tracks nesting depth. Without it the first nested </i> would close
the <button> early, drop its text, and report every icon button as unnamed —
output indistinguishable from a real finding, which is why the control below
exists in both directions.
"""

from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEMPLATE_ROOTS = [REPO / "templates", REPO / "apps"]

NAME_ATTRS = ("aria-label", "aria-labelledby")


class _TooltipNames(HTMLParser):
    """Collect (line, tag, has_name) for every element carrying data-tooltip."""

    VOID = {"img", "input", "br", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.findings = []
        self._stack = []  # entries: dict(tag, line, named, text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        named = bool((a.get("aria-label") or "").strip() or (a.get("aria-labelledby") or "").strip() or (a.get("title") or "").strip())
        if tag in self.VOID:
            if "data-tooltip" in a:
                self.findings.append((self.getpos()[0], tag, named or bool((a.get("alt") or "").strip())))
            return
        self._stack.append({"tag": tag, "line": self.getpos()[0], "tooltip": "data-tooltip" in a, "named": named, "text": ""})

    def handle_data(self, data):
        if self._stack and data.strip():
            # text names every open ancestor, not only the innermost element
            for entry in self._stack:
                entry["text"] += data.strip()

    def handle_endtag(self, tag):
        # close the nearest open element of this tag; depth tracking is the point
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i]["tag"] == tag:
                closed = self._stack[i:]
                del self._stack[i:]
                for entry in closed:
                    if entry["tooltip"]:
                        self.findings.append((entry["line"], entry["tag"], entry["named"] or bool(entry["text"])))
                break


def _unnamed_in(html: str):
    p = _TooltipNames()
    p.feed(html)
    p.close()
    return [(line, tag) for line, tag, named in p.findings if not named]


def test_the_detector_flags_the_shape_and_passes_a_named_control():
    """Both directions, or the sweep below proves nothing."""
    unnamed = _unnamed_in(
        '<button class="x" data-tooltip="Formats" title=""><i class="fas fa-info"></i></button>'
    )
    assert unnamed == [(1, "button")], unnamed
    named = _unnamed_in(
        '<button data-tooltip="Formats" aria-label="Supported file formats"><i class="fas fa-info"></i></button>'
        '<button data-tooltip="Keys" title="Keyboard shortcuts"><i class="fas fa-keyboard"></i></button>'
        '<a data-tooltip="Home"><i class="fas fa-home"></i> Home</a>'
    )
    assert named == [], named


@pytest.mark.parametrize("root", TEMPLATE_ROOTS, ids=lambda p: p.name)
def test_every_tooltip_control_in_the_templates_has_a_name(root):
    unnamed = []
    scanned = 0
    for path in sorted(root.rglob("*.html")):
        if "node_modules" in path.parts or ".old" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "data-tooltip" not in text:
            continue
        scanned += 1
        for line, tag in _unnamed_in(text):
            unnamed.append(f"{path.relative_to(REPO)}:{line} <{tag}>")
    assert scanned >= 1 or root.name == "apps", f"Control: no template under {root} carries data-tooltip"
    assert not unnamed, "tooltip controls with no accessible name (add aria-label, or non-empty title, or text):\n  " + "\n  ".join(unnamed)
