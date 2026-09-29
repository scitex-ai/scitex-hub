"""The allauth social-signup completion page uses the SciTeX auth shell."""

from pathlib import Path
from types import SimpleNamespace

from django import forms
from django.template.loader import render_to_string

TEMPLATE = (
    Path(__file__).resolve().parents[3]
    / "templates/socialaccount/signup.html"
)


def _source() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_social_signup_completion_extends_the_auth_shell():
    # Arrange
    source = _source()
    # Act
    extends_auth_shell = '{% extends "auth_app/auth_base.html" %}' in source
    # Assert
    assert extends_auth_shell


def test_social_signup_completion_posts_to_allauth():
    # Arrange
    source = _source()
    # Act
    posts_to_social_signup = "{% url 'socialaccount_signup' %}" in source
    # Assert
    assert posts_to_social_signup


def test_social_signup_completion_keeps_csrf_protection():
    # Arrange
    source = _source()
    # Act
    has_csrf = "{% csrf_token %}" in source
    # Assert
    assert has_csrf


def test_social_signup_completion_renders_all_visible_fields():
    # Arrange
    source = _source()
    # Act
    renders_fields = "{% for field in form.visible_fields %}" in source
    # Assert
    assert renders_fields


def test_social_signup_completion_preserves_the_redirect_field():
    # Arrange
    source = _source()
    # Act
    preserves_redirect = "{{ redirect_field }}" in source
    # Assert
    assert preserves_redirect


def test_social_signup_completion_has_one_clear_submit_action():
    # Arrange
    source = _source()
    # Act
    submit_count = source.count('type="submit"')
    # Assert
    assert submit_count == 1


def test_social_signup_completion_renders_inside_the_scitex_auth_card():
    # Arrange
    class CompletionForm(forms.Form):
        email = forms.EmailField(initial="researcher@example.org")
        username = forms.CharField(initial="researcher")

    account = SimpleNamespace(
        get_provider=lambda: SimpleNamespace(name="ORCID")
    )
    # Act
    html = render_to_string(
        "socialaccount/signup.html",
        {"form": CompletionForm(), "account": account, "redirect_field": ""},
    )
    # Assert
    assert (
        'class="auth-form"' in html,
        'class="social-signup-form"' in html,
        "You signed in with ORCID" in html,
    ) == (True, True, True)
