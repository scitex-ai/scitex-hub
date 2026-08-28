"""The header badge's context projection must carry every key its templates read.

WHY THIS TEST EXISTS. Django renders a missing dict key as the empty string
(``string_if_invalid`` defaults to ``""``). So when the projection in
``project_app.context_processors`` drops a key that a template reads, the page
renders SILENTLY WRONG — no exception, no log, no failing assertion anywhere —
and the only symptom is a gap in a sentence.

That is exactly what happened. On 2026-07-30 the badge was deliberately changed
from ``allocated`` to ``ready`` (see the comment in global_header.html:
allocation requires a slot that is free AND workspace_ready AND not
quarantined, which only ``ready`` expresses). The projection was not changed
with it. Measured on production 2026-08-28, the badge read:

    <div class="header-visitor-badge-popover-slots"> of 16 visitor slots available</div>

An EMPTY count — not "0 of 16". Django prints an integer 0 as "0", so a blank is
the tell that the key is ABSENT rather than zero. It had been like that for
roughly a month, on the page investors are pointed at.

The test SCANS THE TEMPLATES rather than hard-coding a key list, so a future
template that reads a new key fails here instead of shipping a blank.
"""

import re
from pathlib import Path

from apps.infra.project_app.context_processors import VISITOR_POOL_STATUS_KEYS
from apps.infra.project_app.services.visitor_pool.pool_health import measure_pool

REPO_ROOT = Path(__file__).resolve().parents[3]
SEARCH_ROOTS = (REPO_ROOT / "templates", REPO_ROOT / "apps")
KEY_RE = re.compile(r"visitor_pool_status\.([a-z_]+)")


def _keys_templates_read() -> set[str]:
    keys: set[str] = set()
    for root in SEARCH_ROOTS:
        for html in root.rglob("*.html"):
            keys.update(
                KEY_RE.findall(html.read_text(encoding="utf-8", errors="replace"))
            )
    return keys


def test_the_scan_finds_the_known_reader() -> None:
    """Control: the scanner must find the badge that motivated this test.

    Without this, an empty scan (a moved template, a renamed variable) would
    make the real assertion below pass for free — a gate that cannot fail.
    """
    keys = _keys_templates_read()
    assert keys, (
        "No template reads visitor_pool_status.<key> anywhere under "
        f"{[str(r) for r in SEARCH_ROOTS]}. Either the badge was removed (delete "
        "this test) or the scan is pointed at the wrong tree — do NOT let an "
        "empty scan satisfy the projection test below."
    )
    assert "ready" in keys, (
        "Expected the header badge to read visitor_pool_status.ready. If the "
        "badge deliberately moved to another quantity, update this control."
    )


def test_projection_carries_every_key_the_templates_read() -> None:
    missing = _keys_templates_read() - set(VISITOR_POOL_STATUS_KEYS)
    assert not missing, (
        f"Templates read visitor_pool_status.{sorted(missing)} but the header "
        f"projection only carries {sorted(VISITOR_POOL_STATUS_KEYS)}. Django "
        "renders a missing key as the empty string, so this ships as a blank in "
        "the rendered sentence with no error. Add the key to "
        "VISITOR_POOL_STATUS_KEYS in project_app.context_processors."
    )


def test_the_pool_status_source_supplies_every_projected_key() -> None:
    """The projection indexes its source with ``[]``; a key the source does not
    return raises KeyError inside the cache loader, which the caller swallows
    into "occupancy hidden". That degrades to a MISSING badge rather than a
    blank one — quieter, and just as wrong.

    Read against ``measure_pool``, the single function that builds the dict,
    rather than against a stand-in whose keys we would be choosing ourselves.
    """
    import inspect

    returned = set(
        re.findall(r'^\s{8}"([a-z_]+)":', inspect.getsource(measure_pool), re.M)
    )
    assert "ready" in returned, (
        "Control: measure_pool's return literal was not parsed — the scan below "
        "cannot be trusted. Its shape changed; fix this reader."
    )
    unavailable = set(VISITOR_POOL_STATUS_KEYS) - returned
    assert not unavailable, (
        f"The header projection asks measure_pool for {sorted(unavailable)}, "
        f"which it does not return (it returns {sorted(returned)}). The badge "
        "would disappear entirely via the except branch in "
        "_visitor_pool_status_cached."
    )
