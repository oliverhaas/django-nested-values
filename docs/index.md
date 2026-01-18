# Django Prefetch Values

Enable `.prefetch_related().values()` in Django ORM - returns nested dicts with prefetched relations instead of model instances.

**~4.6x faster** than standard Django ORM for prefetch queries.

## Why Use This?

Django's built-in `.values()` ignores `prefetch_related()`, which means you can't get prefetched relations as nested dictionaries. This package solves that problem.

**Main use case**: APIs (django-ninja, DRF) where data gets passed to Pydantic models or serializers. Instead of hydrating Django model instances just to serialize them back to dicts, fetch the raw values directly from the database.

## Quick Example

```python
from django_prefetch_values import PrefetchValuesQuerySet

class Book(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField("Author")

    objects = PrefetchValuesQuerySet.as_manager()

# Returns dicts with nested prefetched data
books = Book.objects.prefetch_related("authors").values()
# [{"id": 1, "title": "Book 1", "authors": [{"id": 1, "name": "Author 1"}, ...]}, ...]
```

## Performance

For list endpoints with large page sizes (e.g., 1000 items) and multiple relations:

| Approach | Time |
|----------|------|
| Standard Django | ~130ms |
| django-prefetch-values | ~28ms |

## Installation

```bash
pip install django-prefetch-values
```

Or with uv:

```bash
uv add django-prefetch-values
```

## Requirements

- Python 3.13+
- Django 6.0+
