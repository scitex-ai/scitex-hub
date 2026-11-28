from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.auth_app"
    verbose_name = "Auth"

    def ready(self):
        """Initialize the app when Django starts."""
        # Registers the allauth ``user_logged_in`` receiver that records
        # linked identities. Imported for its side effect; the receiver
        # carries a dispatch_uid so a double import cannot double-fire.
        # Failed sign-in counting and second-factor bookkeeping (receivers
        # carry dispatch_uids).
        from apps.infra.auth_app import login_throttle, mfa_enforcement  # noqa: F401
        from apps.infra.auth_app.account_linking import signals  # noqa: F401
