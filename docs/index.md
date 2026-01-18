# Django Prefetch Values

Enable `.prefetch_related().values()` in Django ORM - returns nested dicts with prefetched relations instead of model instances.

This package solves [Django ticket #26565](https://code.djangoproject.com/ticket/26565), which has been open since 2016.

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

## Requirements

- Python 3.13+
- Django 6.0+
