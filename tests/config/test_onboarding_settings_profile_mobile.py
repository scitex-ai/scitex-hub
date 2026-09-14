#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_onboarding_settings_profile_mobile.py
"""First-run surfaces on a phone and in Japanese: /new/, settings, profile, auth.

Site audit 2026-09-14 on the dev preview (compute-03), signed in as a new user:

D3  /new/ at 390px -- the tab menu kept its 220px desktop column beside the
    form, so the form card was 107px wide and the name input 63px ("my-rese").
D7  /accounts/settings/* at 390px -- the first screen was the 13-item settings
    nav; the page's own content started below the fold.
D8  /accounts/profile/ -- the username heading was white on a fixed light-blue
    banner (invisible in dark mode), and the Email row showed a label with no
    value for a user with no email.
D10 Japanese first run -- /auth/signin/ was entirely English, /auth/signup/'s
    labels were English, and /new/ and /accounts/profile/ were entirely English.
Minor -- the profile settings page fetched /static/data/cities_timezones.json
    (404; the file lives under shared/data/), and the tab title named the last
    project ("dotfiles — SciTeX (dev)") on pages that are not about a project.

Every ja assertion has an en control where "no English" alone could pass for a
page that rendered nothing. The .mo catalogs are gitignored, so the module
fixture compiles them with the project's babel-based script.
"""

from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.template import Context, Template
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_NON_TEXT = re.compile(r"<(script|style|svg|pre|code)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# Words that are the same in both languages: product and service names,
# protocols, file formats, and example values shown as data.
_SAME_IN_BOTH = re.compile(
    r"\b(SciTeX|Minimal|Full|GitHub|GitLab|Gitea|Google|ORCID|HPC|SSH|SSHFS|TRIP|"
    r"HTTPS|URL|JSON|YAML|Font Awesome|FA|Git|Writer|Scholar|Code|Viz|App Maker|"
    r"AGPL|GPL|MIT|Apache|BSD|MPL|Proprietary|Clause|TensorBoard|Jupyter|CLI|"
    r"Cloud|Academic|pip|Python|scitex\.ai|username|OEM)\b"
)
_LATIN_WORD = re.compile(r"[A-Za-z]{2,}")

CREATE_CSS = PROJECT_ROOT / "apps/infra/project_app/static/project_app/css/create_mobile.css"
SETTINGS_CSS = PROJECT_ROOT / "static/shared/css/layouts/settings-layout.css"
PROFILE_CSS = PROJECT_ROOT / "apps/infra/accounts_app/static/accounts_app/css/profile.css"


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the ja render reads the real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    translation.trans_real._translations.clear()
    yield


@pytest.fixture
def new_user(django_user_model):
    return django_user_model.objects.create_user(
        username="first-run-user", email="first-run@example.org", password="x-Pass-12345"
    )


@pytest.fixture
def signed_in_client(new_user):
    client = Client()
    client.force_login(new_user)
    return client


@pytest.fixture
def signed_in_client_without_email(django_user_model):
    user = django_user_model.objects.create_user(
        username="no-email-user", email="", password="x-Pass-12345"
    )
    client = Client()
    client.force_login(user)
    return client


def _get(client, path, language):
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
    return client.get(path).content.decode()


def _visible_text(html):
    html = _COMMENT.sub(" ", html)
    html = _NON_TEXT.sub(" ", html)
    html = _TAG.sub(" ", html)
    return _WS.sub(" ", html_lib.unescape(html)).strip()


def _region(html, start_pattern, end_marker):
    match = re.search(start_pattern, html)
    if not match:
        return ""
    end = html.find(end_marker, match.end())
    return html[match.start() : end if end != -1 else len(html)]


def _english_words(text):
    """Latin words left in a ja render once shared names are removed."""
    return _LATIN_WORD.findall(_SAME_IN_BOTH.sub(" ", text))


def _auth_form(html):
    return _region(html, r'<div class="auth-form">', "</form>")


def _create_page(html):
    return _region(html, r'<div class="create-page"', '<div class="create-help-text">')


def _profile_page(html):
    return _region(html, r'<div class="profile-header">', "</main>")


def _compact_summary(html):
    match = re.search(
        r'<details class="settings-nav-compact"[^>]*>\s*<summary[^>]*>(.*?)</summary>', html, re.S
    )
    return _visible_text(match.group(1)) if match else ""


def _title_for(path, **context):
    request = RequestFactory().get(path)
    template = Template("{% load branding_tags %}{% page_title %}")
    return template.render(Context({"request": request, **context}))


# ---------------------------------------------------------------------------
# D3 -- /new/ on a phone
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_new_project_offers_a_compact_type_picker_under_english(signed_in_client):
    # Arrange
    path = reverse("project_create")
    # Act
    html = _get(signed_in_client, path, "en")
    # Assert
    assert re.search(r'<select[^>]*id="create-type-select"', html), "no phone type picker"


@pytest.mark.django_db
def test_new_project_type_picker_label_under_japanese(signed_in_client):
    # Arrange
    path = reverse("project_create")
    # Act
    html = _get(signed_in_client, path, "ja")
    # Assert
    assert re.search(r'<label[^>]*for="create-type-select"[^>]*>\s*プロジェクトの種類', html)


def test_new_project_css_stacks_to_one_full_width_column_on_phones():
    # Arrange
    css = CREATE_CSS.read_text(encoding="utf-8")
    # Act
    phone = re.search(r"@media \(max-width: 768px\) \{(.*?)\n\}", css, re.S)
    # Assert
    assert phone and re.search(
        r"\.create-two-col\s*\{[^}]*flex-direction:\s*column", phone.group(1)
    ) and re.search(r"min-height:\s*44px", phone.group(1)), "no phone single-column rule"


# ---------------------------------------------------------------------------
# D7 -- settings content first on a phone
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_settings_compact_nav_names_the_current_page_under_english(signed_in_client):
    # Arrange
    path = reverse("accounts_app:ssh_keys")
    # Act
    summary = _compact_summary(_get(signed_in_client, path, "en"))
    # Assert
    assert summary == "Settings › SSH keys", summary


@pytest.mark.django_db
def test_settings_compact_nav_names_the_current_page_under_japanese(signed_in_client):
    # Arrange
    path = reverse("accounts_app:ssh_keys")
    # Act
    summary = _compact_summary(_get(signed_in_client, path, "ja"))
    # Assert
    assert summary == "設定 › SSH キー", summary


def test_settings_css_hides_the_full_nav_list_on_phones():
    # Arrange
    css = SETTINGS_CSS.read_text(encoding="utf-8")
    # Act
    phone = re.search(r"@media \(max-width: 768px\) \{(.*?)\n\}", css, re.S)
    # Assert
    assert phone and re.search(
        r"\.settings-nav-full\s*\{[^}]*display:\s*none", phone.group(1)
    ), "the 13-item list still renders above the content on phones"


# ---------------------------------------------------------------------------
# D8 -- profile banner and email
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_shows_the_email_value(signed_in_client):
    # Arrange
    path = reverse("accounts_app:profile")
    # Act
    html = _get(signed_in_client, path, "en")
    # Assert
    assert re.search(
        r'data-profile-field="email".*?<div class="profile-value">\s*first-run@example.org', html, re.S
    )


@pytest.mark.django_db
def test_profile_hides_the_email_row_when_there_is_no_email(signed_in_client_without_email):
    # Arrange
    path = reverse("accounts_app:profile")
    # Act
    html = _get(signed_in_client_without_email, path, "en")
    # Assert
    assert not re.search(r'<div class="profile-label">\s*Email\s*</div>', html)


def test_profile_heading_colour_comes_from_a_theme_token():
    # Arrange
    css = PROFILE_CSS.read_text(encoding="utf-8")
    # Act
    rule = re.search(r"\.profile-header h1\s*\{([^}]*)\}", css)
    # Assert
    assert rule and re.search(r"color:\s*var\(--text-primary\)", rule.group(1)), "heading colour not tokenised"


def test_profile_banner_background_is_not_the_fixed_light_blue():
    # Arrange
    css = PROFILE_CSS.read_text(encoding="utf-8")
    # Act
    rule = re.search(r"\.profile-header\s*\{([^}]*)\}", css)
    # Assert
    assert rule and "--scitex-color-07" not in rule.group(1), rule.group(1) if rule else css


# ---------------------------------------------------------------------------
# D10 -- Japanese first run. Each test reads the en render too: Django returns
# the msgid for a missing translation, so "no English under ja" alone would
# also pass for a region that rendered nothing.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_signin_form_under_japanese_has_no_english():
    # Arrange
    path = reverse("auth_app:signin")
    english = _visible_text(_auth_form(_get(Client(), path, "en")))
    # Act
    text = _visible_text(_auth_form(_get(Client(), path, "ja")))
    # Assert
    assert "Username or Email" in english and _JAPANESE.search(text) and not _english_words(text), _english_words(text)


@pytest.mark.django_db
def test_signup_form_under_japanese_has_no_english():
    # Arrange
    path = reverse("auth_app:signup")
    english = _visible_text(_auth_form(_get(Client(), path, "en")))
    # Act
    text = _visible_text(_auth_form(_get(Client(), path, "ja")))
    # Assert
    assert (
        "Create Account" in english and "Terms of Use" in english
        and _JAPANESE.search(text) and not _english_words(text)
    ), _english_words(text)


@pytest.mark.django_db
def test_new_project_page_under_japanese_has_no_english(signed_in_client):
    # Arrange
    path = reverse("project_create")
    english = _visible_text(_create_page(_get(signed_in_client, path, "en")))
    # Act
    text = _visible_text(_create_page(_get(signed_in_client, path, "ja")))
    # Assert
    assert "Create new project" in english and _JAPANESE.search(text) and not _english_words(text), _english_words(text)


@pytest.mark.django_db
def test_profile_page_under_japanese_has_no_english(signed_in_client):
    # Arrange
    path = reverse("accounts_app:profile")
    english = _visible_text(_profile_page(_get(signed_in_client, path, "en")))
    # Act
    page = _visible_text(_profile_page(_get(signed_in_client, path, "ja")))
    text = page.replace("first-run@example.org", " ").replace("first-run-user", " ")
    # Assert
    assert "Profile Information" in english and _JAPANESE.search(text) and not _english_words(text), _english_words(text)


# ---------------------------------------------------------------------------
# Minor -- cities data path, tab title
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_settings_fetches_cities_from_the_shared_static_path(signed_in_client):
    # Arrange
    path = reverse("accounts_app:profile_edit")
    # Act
    html = _get(signed_in_client, path, "en")
    # Assert
    assert "/static/shared/data/cities_timezones.json" in html and "/static/data/cities_timezones.json" not in html


@pytest.mark.parametrize("path", ["/accounts/profile/", "/accounts/settings/ssh-keys/", "/new/", "/console/"])
def test_non_project_pages_do_not_name_the_last_project_in_the_tab(path):
    # Arrange -- the same context on a project app DOES name the project, so
    # the absence below is the path rule, not a context that never rendered.
    last_project = SimpleNamespace(name="dotfiles", slug="dotfiles")
    project_app_title = _title_for("/apps/writer/", current_project=last_project)
    # Act
    title = _title_for(path, current_project=last_project)
    # Assert
    assert "dotfiles" in project_app_title and "dotfiles" not in title, (project_app_title, title)


@pytest.mark.parametrize(
    ("path", "label"),
    [
        ("/accounts/profile/", "Profile"),
        ("/accounts/settings/ssh-keys/", "Settings"),
        ("/new/", "New project"),
    ],
)
def test_non_project_pages_name_themselves_in_the_tab(path, label):
    # Arrange
    last_project = SimpleNamespace(name="dotfiles", slug="dotfiles")
    # Act
    title = _title_for(path, current_project=last_project)
    # Assert
    assert title.startswith(label + " — SciTeX"), title
