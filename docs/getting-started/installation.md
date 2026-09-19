# Installation

## Supported Versions

|            | Python 3.13 | Python 3.14 |
|------------|:-----------:|:-----------:|
| Django 5.2 | ✓           | ✓           |
| Django 6.0 | ✓           | ✓           |
| Django 6.1 | ✓           | ✓           |

CI also runs the test suite on the free-threaded Python 3.14 build.

## Install from PyPI

```bash
pip install django-nested-values
```

Or with uv:

```bash
uv add django-nested-values
```

The package has no models and does not need an entry in `INSTALLED_APPS`. It imports `django.contrib.contenttypes`, so that app must be installed.

## Development Installation

```bash
git clone https://github.com/oliverhaas/django-nested-values.git
cd django-nested-values
uv sync --group dev --group docs
uv run pytest
```
