from django.apps import AppConfig


class LlmAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.llm_app"
    verbose_name = "LLM Integration"
