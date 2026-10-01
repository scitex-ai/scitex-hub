"""Branding metadata is optional when an isolated leaf renders the host shell."""

import re
from pathlib import Path

import pytest
from django.template import Context, Engine

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "templates/global_base_partials/global_head_meta.html"
)
CASES = [
    ("meta_description", "META_DESCRIPTION_OVERRIDE", "META_DESCRIPTION_DEFAULT"),
    ("og_description", "OG_DESCRIPTION_OVERRIDE", "OG_DESCRIPTION"),
    ("twitter_description", "OG_DESCRIPTION_OVERRIDE", "OG_DESCRIPTION"),
]


def fragment(block):
    match = re.search(
        r"{%% block %s %%}.*?{%% endblock %%}" % block,
        SOURCE.read_text(),
        re.S,
    )
    assert match is not None
    return match.group(0)


@pytest.mark.parametrize("block,override,fallback", CASES)
def test_absent_branding_context_does_not_crash_leaf_metadata(
    block, override, fallback
):
    template = Engine().from_string(fragment(block))
    assert template.render(Context({}, use_l10n=False)) == ""


@pytest.mark.parametrize("block,override,fallback", CASES)
def test_leaf_override_needs_no_fallback_and_is_escaped(block, override, fallback):
    template = Engine().from_string(fragment(block))
    html = template.render(Context({override: "Leaf <description>"}, use_l10n=False))
    assert html == "Leaf &lt;description&gt;"


@pytest.mark.parametrize("block,override,fallback", CASES)
def test_configured_branding_fallback_is_preserved(block, override, fallback):
    template = Engine().from_string(fragment(block))
    context = Context(
        {override: "", fallback: "Configured description"}, use_l10n=False
    )
    assert template.render(context) == "Configured description"


@pytest.mark.parametrize("block,override,fallback", CASES)
def test_leaf_can_still_replace_the_host_block(block, override, fallback):
    engine = Engine(
        loaders=[("django.template.loaders.locmem.Loader", {"host": fragment(block)})]
    )
    template = engine.from_string(
        '{% extends "host" %}{% block ' + block + " %}Leaf block{% endblock %}"
    )
    assert template.render(Context({}, use_l10n=False)) == "Leaf block"
