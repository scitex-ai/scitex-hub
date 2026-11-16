"""Readable summaries preserve leaf text and remain escaped by native templates."""

import pytest

from apps.infra.public_app.services.skill_summary import skill_description_summary


@pytest.mark.parametrize('description,expected', [
    ('[WHAT] Build an app.\n[WHEN] Use for apps.\n[HOW] Install tools.', 'Build an app.'),
    ('[TOPIC] Documentation drift\n[DETAILS] Check source and behavior.', 'Documentation drift — Check source and behavior.'),
    ('[WHAT] Folded description. [WHEN] Select this. [HOW] Run tools.', 'Folded description.'),
    ('  Plain  guidance\nwith whitespace.  ', 'Plain guidance with whitespace.'),
    ('[WHAT](https://example.org) is a Markdown link', '[WHAT](https://example.org) is a Markdown link'),
    ('Keep literal [WHAT] labels here.', 'Keep literal [WHAT] labels here.'),
    ('[NOTE] Keep this custom label.', '[NOTE] Keep this custom label.'),
    ('[TOPIC] One topic [DETAILS] supports [links](https://example.org)', 'One topic — supports [links](https://example.org)'),
    ('[WHAT] <script>unsafe()</script> [HOW] keep original', '<script>unsafe()</script>'),
    ('[WHAT] [WHEN] Only usage guidance.', ''),
    ('|', ''), ('>-', ''), ('  ', ''), (None, ''),
])
def test_display_summary(description, expected):
    # Arrange
    source = description
    # Act
    summary = skill_description_summary(source)
    # Assert
    assert summary == expected


def test_provider_template_displays_summary_and_escapes_leaf_html():
    # Arrange
    from pathlib import Path
    from django.template import Context, Engine
    root = Path(__file__).resolve().parents[3]
    raw = '[WHAT] <script>unsafe()</script> [WHEN] internal selection [HOW] internal setup'
    guide = {'namespace': 'owned', 'name': 'guide', 'url': '/owned/guide', 'description': raw, 'summary': skill_description_summary(raw)}
    engine = Engine(dirs=[root/'apps/workspace/docs_app/templates'], libraries={'i18n':'django.templatetags.i18n'})
    catalog = {'selected_package':'owned', 'selected_skills': {'state':'available', 'entries':[guide]}}
    # Act
    html = engine.get_template('docs_app/partials/interface_provider_catalog.html').render(Context({'interface_catalog':catalog}))
    # Assert
    assert ('&lt;script&gt;unsafe()&lt;/script&gt;' in html, '<script>unsafe()' in html, '[WHAT]' in html, 'internal setup' in html, guide['description'] == raw) == (True, False, False, False, True)
