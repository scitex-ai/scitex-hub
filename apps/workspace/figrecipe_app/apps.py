from django.apps import AppConfig


class FigrecipeAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.figrecipe_app"
    label = "vis_app"  # Keep old label for DB compatibility
    verbose_name = "FigRecipe"
