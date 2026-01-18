# Django Prefetch Values

[![PyPI version](https://img.shields.io/pypi/v/django-prefetch-values.svg)](https://pypi.org/project/django-prefetch-values/)
[![CI](https://github.com/oliverhaas/django-prefetch-values/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/django-prefetch-values/actions/workflows/ci.yml)

An experimental package exploring how to combine `.prefetch_related()` with `.values()` in Django ORM, mainly so this can be used in some test cases to evaluate whether this feature is worth the effort.

This explores a solution to [Django ticket #26565](https://code.djangoproject.com/ticket/26565).

## Quick Example

```python
Book.objects.prefetch_related("authors").values("title", "authors")
# [{"title": "...", "authors": [{"id": 1, "name": "..."}, ...]}]
```

## Documentation

See the [full documentation](https://oliverhaas.github.io/django-prefetch-values/) for installation, usage, and API reference.

## Supported Versions

|         | Python 3.13 | Python 3.14 |
|---------|:-----------:|:-----------:|
| Django 5.2 | ✓ | ✓ |
| Django 6.0 | ✓ | ✓ |

## License

MIT
