# Django Nested Values

[![PyPI version](https://img.shields.io/pypi/v/django-nested-values.svg)](https://pypi.org/project/django-nested-values/)
[![CI](https://github.com/oliverhaas/django-nested-values/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/django-nested-values/actions/workflows/ci.yml)

Adds `.values_nested()` to Django querysets. Rows come back as dictionaries with the `select_related()` and `prefetch_related()` data nested inside, built straight from the database rows without model instances.

## Quick Example

```python
Book.objects.only("title").select_related("publisher").prefetch_related("authors").values_nested()
# [{"id": 1, "title": "...", "publisher_id": 1, "publisher": {...}, "authors": [...]}, ...]
```

## Documentation

See the [full documentation](https://oliverhaas.github.io/django-nested-values/) for installation, usage, and API reference.

## Supported Versions

|            | Python 3.13 | Python 3.14 |
|------------|:-----------:|:-----------:|
| Django 5.2 | ✓           | ✓           |
| Django 6.0 | ✓           | ✓           |
| Django 6.1 | ✓           | ✓           |

CI also runs the test suite on the free-threaded Python 3.14 build.

## License

MIT
