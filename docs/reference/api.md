# API Reference

## PrefetchValuesQuerySet

A custom QuerySet that enables `.prefetch_related().values()` to return nested dictionaries.

Inherits from `django.db.models.QuerySet`.

### Setup

```python
from django_prefetch_values import PrefetchValuesQuerySet

class MyModel(models.Model):
    objects = PrefetchValuesQuerySet.as_manager()
```

### values(*fields, **expressions)

Returns dictionaries with prefetched relations included as nested lists.

```python
Book.objects.prefetch_related("authors").values()
# [{"id": 1, "title": "...", "authors": [{"id": 1, "name": "..."}, ...]}, ...]

Book.objects.prefetch_related("authors").values("id", "title")
# [{"id": 1, "title": "...", "authors": [...]}, ...]
```

### values_list(*fields, flat=False, named=False)

Returns tuples with prefetched relations included.

## Supported Relations

- **ManyToManyField**
- **Reverse ForeignKey** (ManyToOneRel)
- **Reverse ManyToMany** (ManyToManyRel)
- **Nested Prefetches**

## Query Efficiency

Same query count as standard Django prefetching: one query for the main model plus one per prefetch.

```python
# 2 queries: books + authors
Book.objects.prefetch_related("authors").values()

# 3 queries: publishers + books + authors
Publisher.objects.prefetch_related(
    Prefetch("books", queryset=Book.objects.prefetch_related("authors"))
).values()
```

The performance benefit comes from avoiding Django model instantiation.
