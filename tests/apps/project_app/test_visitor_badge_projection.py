"""No template may read ``visitor_pool_status`` while the visitor badge is retired.

This is the post-retirement successor to the badge-projection test. The original
version (2026-07-30) guarded against the header badge reading a key that the
context projection did not carry — Django renders a missing dict key as the
empty string, so the badge shipped with a blank count for a month. The badge
itself was REMOVED 2026-09-11 (visitor retirement, card
drop-visitor-readonly-freemium-20260911): there is no visitor/readonly role
anymore, so no template should read ``visitor_pool_status.<key>`` at all.

The scan direction is therefore inverted: any template that starts reading a
pool-status key fails here, which is the exact moment someone has
re-introduced visitor-badge markup without restoring the context processor —
the same silent-blank failure mode the original test guarded against, just
arriving from the other side.
"""

import re
from pathlib import Path

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


def test_no_template_reads_the_retired_pool_status() -> None:
    keys = _keys_templates_read()
    assert not keys, (
        "Templates read visitor_pool_status.<key> "
        f"({sorted(keys)}) but the visitor badge that consumed it was retired "
        "2026-09-11. Re-introducing the badge without restoring "
        "project_app.context_processors._visitor_pool_status_cached will "
        "ship a blank count — the exact silent failure the predecessor of "
        "this test guarded against."
    )
