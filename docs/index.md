# Django Nested Values

Adds `.values_nested()` to Django querysets. Rows come back as dictionaries with the `select_related()` and `prefetch_related()` data nested inside, built straight from the database rows without model instances.

## Quick Example

```python
from django_nested_values import NestedValuesQuerySet


class Book(models.Model):
    title = models.CharField(max_length=200)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    authors = models.ManyToManyField("Author")

    objects = NestedValuesQuerySet.as_manager()


books = (
    Book.objects
    .only("title")
    .select_related("publisher")
    .prefetch_related("authors")
    .values_nested()
)
# [{"id": 1, "title": "...", "publisher_id": 1, "publisher": {"id": 1, "name": "..."}, "authors": [...]}, ...]
```

## What You Get

- The queryset API you already use: `only()`, `defer()`, `select_related()`, `prefetch_related()`, `Prefetch`, `GenericPrefetch`, slicing, `iterator()` and `async for`.
- Foreign keys and one-to-one relations joined into the main query with `select_related()`.
- Many-to-many, reverse foreign key, generic relations and generic foreign keys with `prefetch_related()`, one query per lookup, the same query count as Django's `prefetch_related()` on model instances.
- Plain dicts straight from the database rows.

## Requirements

- Python 3.13+
- Django 5.2+
- `django.contrib.contenttypes` in `INSTALLED_APPS`
