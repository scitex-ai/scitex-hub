from django.apps import AppConfig


class MyProjectsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.my_projects_app"
    label = "my_projects_app"
    verbose_name = "My Projects"
