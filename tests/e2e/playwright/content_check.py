#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Did the page have CONTENT, or did it merely finish painting?

WHY THIS EXISTS. ``.github/workflows/screenshots.yml`` says its second job
is that "a page that starts erroring is caught by the job that photographs
it". Until this module existed it did not do that. The capture asserted
three things — HTTP < 400, ``body[data-session-role] == "visitor"``, and
``document.body.innerText`` being non-empty — and every one of them passes
on a page that rendered nothing a human would call content.

MEASURED 2026-08-17, from the artifact of a GREEN run on develop
(run 32039805008, 11 PNGs, every assertion satisfied):

  * ``04-figrecipe.png`` — the header strip, and then the entire body
    blank. ``#app-mount`` is the FigRecipe bundle's mount point
    (``figrecipe_app/templates/figrecipe_app/figrecipe_partial.html``);
    nothing had mounted into it.
  * ``02-writer.png`` — the file selector still reading "Loading...",
    the word count still "0", the manuscript pane empty. Those are the
    literal template defaults: ``index_partials/main_editor.html`` ships
    ``<span id="section-selector-text">Loading...</span>`` and
    ``<span id="current-word-count">0</span>``, and the page was
    photographed before anything replaced either.
  * ``10-landing.png`` — the hero demo, which is an ``<img>``, rendered
    as the broken-image placeholder showing its ``alt`` text.

The old check survived all three because the page chrome — header, nav,
footer — supplies plenty of ``innerText`` on its own. "Non-empty body
text" is a test that the SHELL rendered. This module tests that the PAGE
did.

INNERTEXT AND MEASURED GEOMETRY, NEVER TEXTCONTENT. ``textContent``
returns markup that never painted: the contents of a ``display:none``
modal, a collapsed panel, a ``<template>``. Reading it has twice produced
a confident wrong answer about this product. Every string this module
reads comes from ``innerText`` (which follows the CSS rendered-text
rules) or from a direct-child text node on an element that was measured
to have a non-zero box; every "is it there" question is answered by
``getBoundingClientRect`` plus ``getComputedStyle``, not by presence in
the DOM.

ONE NAVIGATION, ONE READ. All of it comes back from a single
``page.evaluate`` so the capture pays one round trip per route and every
assertion in a page's group is reading the SAME moment of that page —
rather than each test re-navigating and quietly measuring a different
render.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Below this many characters of VISIBLE body text, the page did not render
#: content. Deliberately a floor and not a target: the point is to catch a
#: page that is blank or nearly so, not to police how wordy a screen is.
#: The chrome alone (header, nav, footer) clears this on every page in the
#: capture set, which is exactly why it cannot be the only check.
DEFAULT_MIN_BODY_TEXT_CHARS = 80

#: The floor is tunable, because raising it while investigating a page is
#: genuinely useful. It is tunable IN THE OPEN: an override is stated at
#: the top of the content report and repeated on every page line, so a
#: lowered floor shows up in the artifact instead of hiding in the
#: environment.
#:
#: That reporting is the whole safeguard and it is deliberate. An
#: env-overridable threshold is otherwise an off switch for the exact
#: failure this module exists to end — set SCITEX_E2E_MIN_BODY_TEXT=0 in
#: the workflow and the body-text check stops guarding while the job stays
#: green, which is the old defect wearing a knob. A silent knob would be
#: worse than no knob; a loud one is fine.
MIN_BODY_TEXT_CHARS = int(
    os.getenv("SCITEX_E2E_MIN_BODY_TEXT", str(DEFAULT_MIN_BODY_TEXT_CHARS))
)

#: A loading placeholder is SHORT. Prose that happens to begin with the
#: word "loading" is not. Only an element whose own text is at most this
#: long can be a stuck placeholder, so a docs paragraph explaining lazy
#: loading does not fail the capture.
MAX_LOADING_MARKER_CHARS = 60

#: Django serves ``MEDIA_URL`` from ``MEDIA_ROOT`` — ``base_dir / "media"``
#: (``config/settings/settings_static.py``) — which is a RUNTIME VOLUME.
#: ``.gitignore`` line 813 ignores ``media/`` wholesale and ``git ls-files
#: media/`` is empty, so no CI checkout can ever contain these bytes.
RUNTIME_MEDIA_PREFIX = "/media/"

#: Said in full wherever a runtime-media image is reported, because the
#: honest form of "this one cannot pass here" is naming what is missing.
RUNTIME_MEDIA_REASON = (
    "served from MEDIA_URL (%s), which Django reads from MEDIA_ROOT = "
    "base_dir/'media' — a runtime volume that .gitignore excludes and "
    "`git ls-files media/` confirms is empty. A CI checkout has no such "
    "file, so this image 404s here and renders as the broken-image "
    "placeholder in the PNG. It is NOT evidence about production, and it "
    "is NOT a licence to stop checking images: every image served from a "
    "path the repo DOES contain is still required to have loaded."
) % RUNTIME_MEDIA_PREFIX

# ---------------------------------------------------------------------------
# The probe
# ---------------------------------------------------------------------------

#: Per-route element signals, read in the same pass as the generic ones.
#:
#: Each entry maps a human-readable signal name to a CSS selector. The
#: probe reports, for every one: whether the element exists, whether it was
#: measured to occupy a box, that box, its ``innerText``, and how many
#: element children it has. What COUNTS as healthy is decided in Python,
#: per page, by the tests — the probe only measures.
PAGE_ELEMENT_SIGNALS = {
    "/apps/writer/": {
        # index_partials/main_editor.html ships this reading "Loading...".
        # It is replaced by ts/utils/_section-dropdown/SectionDropdown.ts
        # once the file tree resolves; still reading "Loading..." means it
        # never did.
        "file_selector": "#section-selector-text",
        # Same partial ships this as "0". A manuscript with no words in it
        # is the empty editor the operator was shown.
        "word_count": "#current-word-count",
    },
    "/apps/figrecipe/": {
        # figrecipe_partial.html's mount point for the FigRecipe bundle.
        # Present-but-empty is precisely the blank body in 04-figrecipe.png.
        "mount": "#app-mount",
    },
}

#: Read every content signal in one round trip.
#:
#: Takes ``{name: selector}`` and returns a JSON-able record. Pure
#: measurement — it decides nothing, so a change to what counts as broken
#: is a Python change, reviewable next to the reason it was made.
CONTENT_PROBE_JS = """
(selectors) => {
  const boxOf = (el) => {
    const r = el.getBoundingClientRect();
    return { width: Math.round(r.width), height: Math.round(r.height) };
  };

  // Measured, not inferred. An element is "shown" when it has a real box
  // and nothing in its computed style removes it from the render.
  const shown = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (parseFloat(cs.opacity || '1') === 0) return false;
    const box = boxOf(el);
    return box.width > 0 && box.height > 0;
  };

  // Only the element's OWN text: the concatenation of its direct child
  // text nodes. An ancestor therefore contributes nothing, so a stuck
  // placeholder is reported once, on the element that actually holds the
  // string, instead of once per level of wrapper above it.
  const ownText = (el) => {
    let out = '';
    for (const node of el.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) out += node.nodeValue;
    }
    return out.replace(/\\s+/g, ' ').trim();
  };

  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
  const LOADING_RE = /^loading\\b/i;

  const loadingMarkers = [];
  for (const el of document.querySelectorAll('*')) {
    if (SKIP_TAGS.has(el.tagName)) continue;
    const text = ownText(el);
    if (!text || text.length > %(max_marker)d) continue;
    if (!LOADING_RE.test(text)) continue;
    if (!shown(el)) continue;
    loadingMarkers.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      cls: (el.getAttribute('class') || '').slice(0, 120),
      text: text,
      box: boxOf(el),
    });
  }

  // Is this element in the render at all? A broken <img> inside a
  // display:none modal cannot be in the screenshot, and failing on it
  // would be failing on something no reader can see — this product has
  // several such modals, each with its own placeholder image.
  //
  // Layout PARTICIPATION is the question, not box size: a broken image can
  // collapse to 0x0 and must still count, which is exactly the case that
  // has to be caught. `shown()` is deliberately not reused here, because it
  // requires a non-zero box and would therefore excuse the broken image
  // whose box collapsed BECAUSE it was broken.
  const inLayout = (el) => {
    if (el.getClientRects().length === 0 && el.offsetParent === null) {
      return false;
    }
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    return parseFloat(cs.opacity || '1') !== 0;
  };

  const images = [];
  for (const img of document.querySelectorAll('img')) {
    const src = img.getAttribute('src') || '';
    if (!src) continue;
    const rendered = inLayout(img);
    images.push({
      src: src,
      alt: img.getAttribute('alt') || '',
      complete: !!img.complete,
      naturalWidth: img.naturalWidth,
      rendered: !!rendered,
      box: boxOf(img),
    });
  }

  const elements = {};
  for (const name of Object.keys(selectors || {})) {
    const el = document.querySelector(selectors[name]);
    elements[name] = el === null
      ? { selector: selectors[name], present: false }
      : {
          selector: selectors[name],
          present: true,
          shown: shown(el),
          box: boxOf(el),
          text: (el.innerText || '').replace(/\\s+/g, ' ').trim(),
          childElementCount: el.childElementCount,
        };
  }

  const bodyText = (document.body ? (document.body.innerText || '') : '').trim();
  return {
    url: location.pathname,
    bodyText: bodyText,
    bodyTextChars: bodyText.length,
    loadingMarkers: loadingMarkers,
    images: images,
    elements: elements,
  };
}
""" % {"max_marker": MAX_LOADING_MARKER_CHARS}


def read_content_signals(page, selectors=None):
    """Measure everything this module checks, in one ``page.evaluate``.

    Args:
        page: a Playwright page, already navigated and hydrated. This
            function does NOT wait — waiting is
            ``page_ready.wait_for_page_ready``'s job, and doing it in two
            places is how one of them quietly stops happening.
        selectors: ``{name: css_selector}`` for the page-specific signals,
            or ``None`` for the generic ones only.

    Returns:
        dict: the raw measurement. Nothing is judged here.
    """
    return page.evaluate(CONTENT_PROBE_JS, selectors or {})


# ---------------------------------------------------------------------------
# Judgements — each returns the FAILURE TEXT, or "" when the page is fine
# ---------------------------------------------------------------------------


def body_text_problem(signals, where):
    """Non-empty is not the same as non-blank. Require a floor."""
    chars = signals["bodyTextChars"]
    if chars >= MIN_BODY_TEXT_CHARS:
        return ""
    return (
        "%s rendered %d characters of visible body text, below the %d-char "
        "floor.\n"
        "  This is the blank-page failure the capture exists to catch: the "
        "PNG would show a shell with nothing in it.\n"
        "  what was visible: %r"
        % (where, chars, MIN_BODY_TEXT_CHARS, signals["bodyText"][:400])
    )


def loading_marker_problem(signals, where):
    """A placeholder still on screen means hydration did not finish."""
    markers = signals["loadingMarkers"]
    if not markers:
        return ""
    lines = [
        "  %s%s%s reading %r (%dx%d px)"
        % (
            m["tag"],
            "#" + m["id"] if m["id"] else "",
            "." + m["cls"].split()[0] if m["cls"].strip() else "",
            m["text"],
            m["box"]["width"],
            m["box"]["height"],
        )
        for m in markers
    ]
    return (
        "%s was photographed with %d loading placeholder(s) still on "
        "screen, after the hydration wait had already returned:\n%s\n"
        "  Each of these is a container that never received its content. "
        "Waiting longer is not the fix — find out why the content never "
        "arrived." % (where, len(markers), "\n".join(lines))
    )


def split_broken_images(signals):
    """Broken images, split into the ones that are this repo's problem.

    An image is broken when the browser FINISHED with it (``complete``)
    and got no pixels (``naturalWidth == 0``). A lazy image that has not
    started is not ``complete`` and is not counted; an image with no
    ``src`` at all was never collected.

    Returns:
        tuple: ``(failing, runtime_media)``. ``runtime_media`` are the
        ones served from ``MEDIA_URL``, which no CI checkout can contain
        — reported, never silently dropped. Everything else fails.
    """
    broken = [
        img
        for img in signals["images"]
        if img["rendered"] and img["complete"] and img["naturalWidth"] == 0
    ]
    runtime_media = [
        img for img in broken if img["src"].startswith(RUNTIME_MEDIA_PREFIX)
    ]
    failing = [img for img in broken if not img["src"].startswith(RUNTIME_MEDIA_PREFIX)]
    return failing, runtime_media


def broken_image_problem(signals, where):
    """Every image the repo can actually serve must have loaded."""
    failing, _ = split_broken_images(signals)
    if not failing:
        return ""
    lines = [
        "  <img src=%r alt=%r> loaded 0x0 (box %dx%d px)"
        % (img["src"], img["alt"], img["box"]["width"], img["box"]["height"])
        for img in failing
    ]
    return (
        "%s has %d broken image(s) — the browser finished loading them and "
        "got no pixels, so each renders as the placeholder-with-alt-text a "
        "reader sees as a broken page:\n%s" % (where, len(failing), "\n".join(lines))
    )


def undeclared_absent_media_problem(signals, declared, where):
    """A runtime-media image may be absent here ONLY if it is declared.

    ``RUNTIME_MEDIA_PREFIX`` explains why a ``/media/`` image cannot load in
    CI, but "explained" must not become "unchecked". Each such image has to
    be named, per page, in the capture's declaration table. A new broken
    ``/media/`` image therefore fails until somebody writes down which file
    it is and why the repo does not carry it — which is a code change in a
    diff, not a check quietly widening on its own.

    Args:
        signals: a ``read_content_signals`` measurement.
        declared: the src strings declared absent for THIS page.
        where: human label for the page.
    """
    _, runtime_media = split_broken_images(signals)
    undeclared = [img for img in runtime_media if img["src"] not in declared]
    if not undeclared:
        return ""
    lines = ["  <img src=%r alt=%r>" % (img["src"], img["alt"]) for img in undeclared]
    return (
        "%s has %d UNDECLARED broken image(s) under %s:\n%s\n"
        "  %s\n"
        "  If this file is genuinely runtime-only, add its src to "
        "DECLARED_ABSENT_MEDIA for this page with the reason. If it is "
        "supposed to ship with the repo, it is a real broken image — fix "
        "the reference, do not declare it."
        % (
            where,
            len(undeclared),
            RUNTIME_MEDIA_PREFIX,
            "\n".join(lines),
            RUNTIME_MEDIA_REASON,
        )
    )


def missing_element_problem(signals, name, where):
    """The named signal must exist and occupy a box."""
    el = signals["elements"].get(name)
    if el is None:
        return (
            "%s: no signal named %r was probed. PAGE_ELEMENT_SIGNALS and "
            "the test asking for it have drifted apart." % (where, name)
        )
    if not el["present"]:
        return (
            "%s: %s (%s) is not in the DOM at all. The page rendered "
            "something other than the screen this capture claims to "
            "photograph." % (where, name, el["selector"])
        )
    if not el["shown"]:
        return (
            "%s: %s (%s) is in the DOM but was measured at %dx%d px and is "
            "not rendered. Nothing of it is in the PNG."
            % (
                where,
                name,
                el["selector"],
                el["box"]["width"],
                el["box"]["height"],
            )
        )
    return ""


def empty_container_problem(signals, name, where):
    """A mount point that exists and is empty is the blank-body failure."""
    missing = missing_element_problem(signals, name, where)
    if missing:
        return missing
    el = signals["elements"][name]
    if el["childElementCount"] > 0 or el["text"]:
        return ""
    return (
        "%s: %s (%s) is mounted at %dx%d px and is EMPTY — no child "
        "elements, no visible text.\n"
        "  This is the '04-figrecipe.png' failure exactly: the container "
        "painted, the app never mounted into it, and the PNG shows a "
        "header strip above a blank page."
        % (
            where,
            name,
            el["selector"],
            el["box"]["width"],
            el["box"]["height"],
        )
    )


def stuck_placeholder_problem(signals, name, where):
    """This specific named element must have moved past 'Loading...'."""
    missing = missing_element_problem(signals, name, where)
    if missing:
        return missing
    text = signals["elements"][name]["text"]
    if not text.lower().startswith("loading"):
        return ""
    return (
        "%s: %s (%s) still reads %r. That is the template's shipped "
        "default, not a resolved value — nothing ever replaced it."
        % (where, name, signals["elements"][name]["selector"], text)
    )


def nonzero_count_problem(signals, name, where):
    """A count element whose value is still zero counted nothing."""
    missing = missing_element_problem(signals, name, where)
    if missing:
        return missing
    text = signals["elements"][name]["text"]
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits and int(digits) > 0:
        return ""
    return (
        "%s: %s (%s) reads %r — no positive count. The screen was "
        "photographed with nothing loaded into it."
        % (where, name, signals["elements"][name]["selector"], text)
    )


# ---------------------------------------------------------------------------
# Reporting — say what was found AND what was not, for every page
# ---------------------------------------------------------------------------


class BrowserProblemLog:
    """What the BROWSER complained about while a route was being measured.

    WHY THIS EXISTS. "``#app-mount`` is 1910x1015 px with zero children"
    says a page is broken; it does not say why, and every "why" so far has
    cost a full CI round trip to answer. The browser already knew: it had
    the failing request and the thrown exception in hand at the moment of
    the screenshot, and threw them away.

    Concretely — run 32056013931 spent ~13 minutes proving that every
    ``/static/vite/*.js`` answered HTTP 500. That fact was in the response
    stream of the very page being measured. Recorded here, the same run
    would have printed it next to the empty mount it caused.

    Three sources, because they fail differently and a page can hit any
    one of them alone:

      * a response with status >= 400 — the asset or API that did not
        arrive (this is the one that would have named the 500s);
      * an uncaught page exception — the script that loaded and then died,
        which leaves a mount point painted and empty;
      * a ``console.error`` — including the product's own
        ``_manifest_miss`` marker, which reports a missing Vite entry via
        exactly that channel in production.

    Capped per route. A page whose every request fails should say so in a
    line or two, not bury the report it is attached to.
    """

    MAX_PER_ROUTE = 20

    def __init__(self):
        self._items = []

    def attach(self, page):
        """Subscribe to the page's problem streams. Call once per page."""
        page.on("response", self._on_response)
        page.on("pageerror", self._on_page_error)
        page.on("console", self._on_console)

    def reset(self):
        """Forget the previous route's problems."""
        self._items = []

    def drain(self):
        """The problems seen since the last ``reset``."""
        return list(self._items)

    def _record(self, text):
        if len(self._items) < self.MAX_PER_ROUTE:
            self._items.append(text)
        elif len(self._items) == self.MAX_PER_ROUTE:
            self._items.append("... further problems suppressed")

    def _on_response(self, response):
        try:
            status = response.status
        except Exception:  # the page navigated away mid-read
            return
        if status >= 400:
            self._record("HTTP %d %s" % (status, response.url))

    def _on_page_error(self, error):
        self._record("uncaught exception: %s" % str(error).split("\n")[0])

    def _on_console(self, message):
        try:
            if message.type != "error":
                return
            self._record("console.error: %s" % message.text[:300])
        except Exception:
            return


def describe_browser_problems(problems):
    """Render the browser's complaints for the report, or say there were none."""
    if not problems:
        return "  browser errors ....... none"
    lines = ["  browser errors ....... %d" % len(problems)]
    lines.extend("      %s" % p for p in problems)
    return "\n".join(lines)


def threshold_banner():
    """State the thresholds this run actually used, and flag overrides.

    A threshold nobody can see is a threshold nobody can audit. The floor
    is env-tunable on purpose, so the report says what it is EVERY run and
    says loudly when it is not the default — because "the job is green"
    means nothing if the bar was quietly moved to zero, and that is the
    precise shape of the defect this module was written to end.
    """
    line = "body-text floor: %d chars" % MIN_BODY_TEXT_CHARS
    if MIN_BODY_TEXT_CHARS == DEFAULT_MIN_BODY_TEXT_CHARS:
        return line + " (default)"
    return line + (
        " -- OVERRIDDEN via SCITEX_E2E_MIN_BODY_TEXT (default %d).\n"
        "  %s Anything below the default weakens this gate; read the\n"
        "  per-page character counts below before trusting a green run."
        % (
            DEFAULT_MIN_BODY_TEXT_CHARS,
            (
                "RAISED — stricter than default."
                if MIN_BODY_TEXT_CHARS > DEFAULT_MIN_BODY_TEXT_CHARS
                else "LOWERED — WEAKER than default."
            ),
        )
    )


def describe_signals(where, signals):
    """A per-page found/not-found report.

    Printed and written next to the PNGs. A page that legitimately has no
    content should SAY so in the artifact rather than be silently skipped:
    whoever downloads the screenshots gets, alongside each image, the
    measurement that image was passed on.
    """
    failing, runtime_media = split_broken_images(signals)
    lines = [
        "=== %s" % where,
        "  body text ........... %s (%d chars, floor %d)"
        % (
            "FOUND" if signals["bodyTextChars"] >= MIN_BODY_TEXT_CHARS else "NOT FOUND",
            signals["bodyTextChars"],
            MIN_BODY_TEXT_CHARS,
        ),
        "  loading placeholders  %s"
        % (
            "none left"
            if not signals["loadingMarkers"]
            else "STILL ON SCREEN: "
            + ", ".join(repr(m["text"]) for m in signals["loadingMarkers"])
        ),
        "  images ............... %d rendered, %d broken, %d absent runtime media"
        % (
            sum(1 for i in signals["images"] if i["rendered"]),
            len(failing),
            len(runtime_media),
        ),
    ]
    for img in runtime_media:
        lines.append("      NOT FOUND (expected here): %s" % img["src"])
        lines.append("        reason: %s" % RUNTIME_MEDIA_REASON)
    for img in failing:
        lines.append("      BROKEN: %s (alt=%r)" % (img["src"], img["alt"]))
    for name, el in sorted(signals["elements"].items()):
        if not el["present"]:
            lines.append(
                "  %s ... NOT FOUND (%s absent from DOM)" % (name, el["selector"])
            )
            continue
        lines.append(
            "  %s ... %s %s (%dx%d px, %d children) text=%r"
            % (
                name,
                "FOUND" if el["shown"] else "PRESENT BUT NOT RENDERED",
                el["selector"],
                el["box"]["width"],
                el["box"]["height"],
                el["childElementCount"],
                el["text"][:80],
            )
        )
    return "\n".join(lines)


# EOF
