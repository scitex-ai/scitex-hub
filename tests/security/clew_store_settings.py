"""Isolated settings for the Clew HTTP/store integration tests.

No deployed settings, dotenv files, provisioner signals, or Gitea connections
are loaded. Use an explicitly supplied disposable local PostgreSQL cluster:

python -m django test tests.security.test_clew_tenant_store \
    --settings=tests.security.clew_store_settings --noinput
"""

import os
from pathlib import Path
from uuid import uuid4

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from psycopg.conninfo import conninfo_to_dict


class QuietProjectApp(AppConfig):
    name = "apps.infra.project_app"


class QuietOrganizationsApp(AppConfig):
    name = "apps.infra.organizations_app"


BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = "synthetic-test-only-not-a-deployment-key"  # pragma: allowlist secret
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "scitex_app",
    "scitex_sdk.ui",
    "tests.security.clew_store_settings.QuietOrganizationsApp",
    "tests.security.clew_store_settings.QuietProjectApp",
    "scitex_clew._django.apps.ClewAppConfig",
]
MIGRATION_MODULES = dict.fromkeys(
    ("auth", "contenttypes", "sessions", "organizations_app", "project_app", "clew_app")
)
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
SCITEX_PROJECT_PROVIDER = "apps.infra.project_app.services.project_scope.HubProjectProvider"
SCITEX_PROJECT_STORAGE = "apps.infra.project_app.services.project_scope.HubProjectStorage"
SCITEX_PROJECT_STORE = "apps.infra.project_app.services.project_store.HubProjectStore"
ROOT_URLCONF = "tests.security.clew_store_settings"
ALLOWED_HOSTS = ["testserver"]
STATIC_URL = "/static/"
DEBUG = True
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.template.context_processors.csrf"]}}]
SCITEX_PROJECT_PROVIDER_URL = "project-list"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
dsn = os.environ.get("SCITEX_CLEW_TEST_ADMIN_DSN")
if not dsn:
    raise ImproperlyConfigured(
        "Explicit disposable SCITEX_CLEW_TEST_ADMIN_DSN required"
    )
parameters = conninfo_to_dict(dsn)
port = int(parameters.get("port", 5432))
host = parameters.get("host", "")
if port in {5432, 5433, 55432, 55433} or not (
    host in {"127.0.0.1", "localhost"} or host.startswith("/")
):
    raise ImproperlyConfigured("Use a disposable local cluster on an ephemeral port")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parameters.get("dbname", "postgres"),
        "USER": parameters["user"],
        "HOST": host,
        "PORT": port,
        "PASSWORD": parameters.get("password", ""),
        "TEST": {"NAME": "test_clew_http_" + uuid4().hex[:12]},
    }
}


# Delay URL imports until the app registry is populated.
def __getattr__(name):
    if name == "urlpatterns":
        from django.urls import path
        from scitex_sdk.ui import project_scope

        from apps.workspace.apps_app.services.plugin_apps import plugin_urlpatterns

        def projects(request):
            return project_scope.project_listing_view(project_scope.host_project_provider())(request)

        return plugin_urlpatterns([]) + [path("project-list/", projects, name="project-list")]
    raise AttributeError(name)
