#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The header ships ONE project selector, so its three ids are unique.

templates/global_base_partials/global_header.html carried TWO copies of the
project selector: the live ``.header-project-selector-inline`` block and a
second ``.header-project-selector`` block that
static/shared/css/components/header/02-layout.css:19-21 hides with
``display: none !important``. The dead copy rendered nothing but still
emitted duplicate ``project-selector-toggle`` / ``project-selector-text`` /
``project-selector-dropdown`` ids — invalid HTML, and a live trap: every
consumer reaches these through ``querySelector``/``getElementById``, which
return the FIRST match in document order, so which element the JS bound was
decided by nothing more than block ordering in the template.

WHY ``== 1`` AND NOT ``<= 1``. The obvious spelling of "not duplicated" is
``count <= 1``, and it is a gate that cannot fail in the direction that
matters: a page whose selector vanished entirely scores 0, and 0 <= 1 is
green. That is the same asymmetry that kept the sibling mobile-menu test
passing while the menu leaked (see test_header_mobile_menu_gate.py) — a
negative assertion over a string that exists nowhere is vacuously true.
``count == 1`` is the positive and the negative in one expression: it fails
at 0 (selector gone / page 500'd / id renamed) and fails at 2 (the dead copy
came back). Neither failure mode can hide.

The id is matched in its ``id="..."`` ATTRIBUTE form, not as a bare string.
``project-selector-text`` and ``project-selector-dropdown`` are also CLASS
names used by an unrelated surface (repo_app/partials/user_profile_content.html),
so the bare strings would count those too and the assertion would be about
the wrong markup.

Counting alone cannot tell WHICH copy survived — deleting the live block and
keeping the hidden one also yields exactly one of each. So the last test
pins the surviving toggle to its ``.header-project-selector-inline``
ancestor, which is the invariant consumers actually depend on.

Real Django test client, no mocks — the assertions are about bytes a browser
receives, not about template source. One assertion per test (STX-TQ007).
"""

from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import TestCase

LIVE_CONTAINER_CLASS = "header-project-selector-inline"

SELECTOR_IDS = (
    "project-selector-toggle",
    "project-selector-text",
    "project-selector-dropdown",
)


class _AncestorClassCollector(HTMLParser):
    """Records the class names enclosing the element carrying ``target_id``.

    ``html.parser`` is deliberate: it is the lenient reader, so a stray
    attribute quirk degrades into a recovered tag rather than an exception
    that would read as "id absent" and turn a real duplicate into a pass.
    """

    def __init__(self, target_id):
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.ancestor_classes = set()
        self._stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if attrs.get("id") == self.target_id:
            for enclosing in self._stack:
                self.ancestor_classes.update(enclosing)
        self._stack.append(classes)

    def handle_startendtag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == self.target_id:
            for enclosing in self._stack:
                self.ancestor_classes.update(enclosing)

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()


class HeaderProjectSelectorIdsUniqueTest(TestCase):
    """Each project-selector id appears exactly once in the rendered page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="selector-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _rendered_home(self):
        """The bytes a logged-in browser receives for ``/``."""
        self.client.force_login(self.user)
        return self.client.get("/").content

    @staticmethod
    def _id_attribute(element_id):
        """``id="<element_id>"`` — the attribute form, not the bare string."""
        return 'id="{}"'.format(element_id).encode()

    def test_toggle_id_absent_from_header(self):
        """The header project switcher was removed 2026-09-11 (operator: no
        project switcher in the global header; selection lives on the
        project/workspace surface). The toggle id must NOT render on ``/``."""
        marker = self._id_attribute("project-selector-toggle")
        content = self._rendered_home()
        assert content.count(marker) == 0

    def test_text_id_absent_from_header(self):
        marker = self._id_attribute("project-selector-text")
        content = self._rendered_home()
        assert content.count(marker) == 0

    def test_dropdown_id_absent_from_header(self):
        marker = self._id_attribute("project-selector-dropdown")
        content = self._rendered_home()
        assert content.count(marker) == 0

    def test_no_selector_id_present_in_header(self):
        content = self._rendered_home()
        counts = {
            element_id: content.count(self._id_attribute(element_id))
            for element_id in SELECTOR_IDS
        }
        assert all(count == 0 for count in counts.values()), counts

    def test_no_live_inline_container_in_header(self):
        """The .header-project-selector-inline container is gone too — not just
        the inner ids, so a half-removed block can't leak back in."""
        content = self._rendered_home().decode("utf-8", "replace")
        assert 'class="header-project-selector-inline"' not in content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
