SECRET_KEY = "isolated-maintenance-tests"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
INSTALLED_APPS = []
DATABASES = {}
ROOT_URLCONF = "tests.platform.test_maintenance_admission"
MIDDLEWARE = ["apps.infra.public_app.middleware_maintenance.MaintenanceMiddleware"]
USE_TZ = True
