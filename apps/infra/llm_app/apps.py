import threading

from django.apps import AppConfig


class LlmAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra.llm_app"
    verbose_name = "LLM Integration"

    def ready(self):
        """Pre-warm the provider/model cache in a background thread at startup."""
        thread = threading.Thread(
            target=self._prewarm_providers,
            daemon=True,
            name="llm-prewarm",
        )
        thread.start()
        self._discover_skills()

    def _discover_skills(self):
        """Auto-discover skill.py from all installed apps."""
        import importlib
        import logging

        from django.apps import apps as django_apps

        logger = logging.getLogger(__name__)

        for app_config in django_apps.get_app_configs():
            module_name = f"{app_config.name}.skill"
            try:
                importlib.import_module(module_name)
                logger.debug(f"Loaded skill from {module_name}")
            except ImportError:
                pass  # App doesn't have a skill.py, that's fine
            except Exception as e:
                logger.warning(f"Error loading skill from {module_name}: {e}")

    @staticmethod
    def _prewarm_providers():
        try:
            from apps.infra.llm_app.utils import get_all_providers_cached

            get_all_providers_cached()
        except Exception:
            pass  # Non-critical: page will still work, just slow on first hit
