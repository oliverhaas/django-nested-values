"""Django settings for benchmarks."""

SECRET_KEY = "benchmark-secret-key"

DEBUG = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "benchmarks",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "benchmark.db",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
