#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The App Store names apps the way a human would, never the raw slug.

WHAT WAS ON PRODUCTION, 2026-08-16. Every card on https://scitex.ai/apps/store/
— the page the operator says he will definitely show — was titled with the
lowercase slug:

    writer   scholar   figrecipe   clew   discovery   tools   docs
    comms    storage   todo

The template read:

    {% if mod_item.reg %}{{ mod_item.reg.label }}
    {% else %}{{ mod_item.app.module_name }}{% endif %}

so whenever the runtime registry entry was not resolved it fell all the way
back to `module_name`, which IS the slug. `AppsModule.label` — the model's
own field, help_text "Human-readable display name (manifest.json 'label')" —
was never consulted, and it is populated: Writer, Scholar, FigRecipe,
Console.

The intent was already written down and still not honoured. detail.html
carried, in a comment, on the line above the slug fallback:

    Registry label ("Storage"), same precedence as the browse cards
    — never the raw slug

and config/branding.py states the same contract for tab titles:
"Capitalization here is the contract: 'Cards', never 'cards'".

WHAT THIS GUARDS: the precedence, at the point where the template actually
renders it — registry label, then the model's label, then the slug as a last
resort so a label-less app still shows something rather than an empty
heading. It renders the REAL template file rather than asserting on its
source, because "the file contains the right tag" is a check on the artefact
I edited, not on what a visitor sees.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

TEMPLATE = "apps_app/partials/module_card.html"


def _mod_item(*, reg_label=None, app_label="", module_name="writer"):
    """Shape the template expects, with only the fields it reads."""
    return SimpleNamespace(
        reg=SimpleNamespace(label=reg_label, name=module_name, icon_fa="") if reg_label else None,
        app=SimpleNamespace(
            module_name=module_name,
            label=app_label,
            short_description="",
            category="utility",
            get_category_display=lambda: "Utility",
            is_builtin=False,
            visibility="public",
            author=None,
            install_count=0,
            star_count=0,
            avg_rating=0,
        ),
        is_dev=False,
        dev_owner="",
        dev_repo="",
    )


def _render(mod_item) -> str:
    return render_to_string(TEMPLATE, {"mod_item": mod_item})


class TestStoreShowsHumanNames:
    @pytest.mark.guards(
        defect=(
            "the App Store card fell back from the registry label straight to "
            "module_name, so every unresolved app was titled with its "
            "lowercase slug on the public store page"
        )
    )
    def test_the_model_label_is_used_when_the_registry_is_unresolved(self):
        # Arrange — exactly the production shape: no registry entry, label set.
        mod_item = _mod_item(reg_label=None, app_label="Writer")

        # Act
        html = _render(mod_item)

        # Assert
        assert "Writer" in html, (
            "the card did not use AppsModule.label; it is almost certainly "
            "showing the raw slug again"
        )

    def test_the_registry_label_still_wins_when_present(self):
        # Arrange
        mod_item = _mod_item(reg_label="FigRecipe", app_label="Ignored")

        # Act
        html = _render(mod_item)

        # Assert
        assert "FigRecipe" in html

    def test_the_slug_remains_the_last_resort(self):
        # Arrange — an app with no human name anywhere.
        mod_item = _mod_item(reg_label=None, app_label="", module_name="todo")

        # Act
        html = _render(mod_item)

        # Assert — better a slug than an empty heading.
        assert "todo" in html
