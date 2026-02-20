import threading

from django.apps import AppConfig


class LlmAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.llm_app"
    verbose_name = "LLM Integration"

    def ready(self):
        """Pre-warm the provider/model cache in a background thread at startup."""
        thread = threading.Thread(
            target=self._prewarm_providers,
            daemon=True,
            name="llm-prewarm",
        )
        thread.start()

    @staticmethod
    def _prewarm_providers():
        try:
            from apps.llm_app.utils import get_all_providers_cached

            get_all_providers_cached()
        except Exception:
            pass  # Non-critical: page will still work, just slow on first hit
