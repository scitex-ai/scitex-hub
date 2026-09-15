from pathlib import Path
from types import SimpleNamespace

from apps.infra.auth_app.checks import (
    SMTP_BACKEND,
    email_delivery_configuration_errors,
)


def _settings(**overrides):
    values = {
        "EMAIL_DELIVERY_REQUIRED": True,
        "EMAIL_BACKEND": SMTP_BACKEND,
        "EMAIL_HOST": "smtp.scitex.test",
        "EMAIL_HOST_USER": "no-reply@scitex.test",
        "EMAIL_HOST_PASSWORD": "configured-secret",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_required_email_delivery_accepts_complete_smtp_configuration():
    assert email_delivery_configuration_errors(_settings()) == []


def test_optional_email_delivery_allows_console_backend():
    configured = _settings(
        EMAIL_DELIVERY_REQUIRED=False,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    )
    assert email_delivery_configuration_errors(configured) == []


def test_required_email_delivery_rejects_console_and_placeholders_safely():
    configured = _settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_HOST_USER="no-reply@example.com",
        EMAIL_HOST_PASSWORD="CHANGE_ME_EMAIL_PASSWORD",
    )

    errors = email_delivery_configuration_errors(configured)

    assert [error.id for error in errors] == ["auth_app.E001"]
    message = errors[0].msg
    assert "SCITEX_HUB_EMAIL_BACKEND" in message
    assert "SCITEX_HUB_EMAIL_HOST" in message
    assert "SCITEX_HUB_EMAIL_HOST_USER" in message
    assert "SCITEX_HUB_EMAIL_HOST_PASSWORD" in message
    assert "CHANGE_ME_EMAIL_PASSWORD" not in message


def test_dev_env_template_requires_real_scitex_smtp_delivery():
    template = (
        Path(__file__).parents[3] / "deployment/docker/envs/.env.example"
    ).read_text()

    assert "SCITEX_HUB_EMAIL_DELIVERY_REQUIRED=True" in template
    assert "SCITEX_HUB_EMAIL_HOST=mail1030.onamae.ne.jp" in template
    assert "SCITEX_HUB_EMAIL_HOST_USER=no-reply@scitex.ai" in template


def test_dev_daphne_runner_executes_django_checks_before_listening():
    runner = (
        Path(__file__).parents[3]
        / "deployment/docker/docker_dev/run_daphne_with_autoreload.py"
    ).read_text()

    assert 'call_command("check")' in runner
    assert runner.index('call_command("check")') < runner.index(
        "autoreload.run_with_reloader"
    )
