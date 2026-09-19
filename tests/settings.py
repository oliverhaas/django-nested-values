"""Django settings for the test suite."""

SECRET_KEY = "test-secret-key"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "tests",
    "tests.testapp",
    "tests.relations",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
    "other": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
