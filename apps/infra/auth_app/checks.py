"""Django system checks for authentication delivery dependencies."""

from django.conf import settings
from django.core.checks import Error, register

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
PLACEHOLDER_MARKERS = ("example.com", "change_me", "changeme")


def email_delivery_configuration_errors(settings_obj=settings):
    """Return safe diagnostics without ever including credential values."""
    if not getattr(settings_obj, "EMAIL_DELIVERY_REQUIRED", False):
        return []

    invalid = []
    if getattr(settings_obj, "EMAIL_BACKEND", "") != SMTP_BACKEND:
        invalid.append("SCITEX_HUB_EMAIL_BACKEND must select Django's SMTP backend")

    for setting_name, env_name in (
        ("EMAIL_HOST", "SCITEX_HUB_EMAIL_HOST"),
        ("EMAIL_HOST_USER", "SCITEX_HUB_EMAIL_HOST_USER"),
        ("EMAIL_HOST_PASSWORD", "SCITEX_HUB_EMAIL_HOST_PASSWORD"),
    ):
        value = str(getattr(settings_obj, setting_name, "") or "")
        if not value or any(marker in value.lower() for marker in PLACEHOLDER_MARKERS):
            invalid.append(
                f"{env_name} must be configured with a non-placeholder value"
            )

    if not invalid:
        return []

    return [
        Error(
            "Real email delivery is required but SMTP is not ready: "
            + "; ".join(invalid),
            hint=(
                "Configure the SCITEX_HUB_EMAIL_* variables and verify the mailbox "
                "credential with the provider. Credential values are intentionally omitted."
            ),
            id="auth_app.E001",
        )
    ]


@register()
def check_email_delivery_configuration(app_configs, **kwargs):
    return email_delivery_configuration_errors()
