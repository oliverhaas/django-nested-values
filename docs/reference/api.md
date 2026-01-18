# API Reference

## PrefetchValuesQuerySet

A custom QuerySet that enables `.prefetch_related().values()` to work together, returning nested dictionaries with prefetched relations.

Inherits from `django.db.models.QuerySet`.

### Usage

Add as a manager to your model:

```python
from django_prefetch_values import PrefetchValuesQuerySet

class MyModel(models.Model):
    objects = PrefetchValuesQuerySet.as_manager()
```

### Methods

#### values(*fields, **expressions)

Returns dictionaries for each row, including prefetched relations as nested lists.

When combined with `prefetch_related()`, the prefetched data is included in each dictionary under the relation name.

**Parameters:**

- `fields` - Field names to include. If empty, includes all fields.
- `expressions` - Annotated expressions to include.

**Returns:** ValuesQuerySet yielding dictionaries

**Example:**

```python
# All fields
Book.objects.prefetch_related("authors").values()
# [{"id": 1, "title": "...", "authors": [{"id": 1, "name": "..."}, ...]}, ...]

# Specific fields
Book.objects.prefetch_related("authors").values("id", "title")
# [{"id": 1, "title": "...", "authors": [...]}, ...]
```

#### values_list(*fields, flat=False, named=False)

Returns tuples for each row. Prefetched relations are included as nested lists within the tuples.

**Parameters:**

- `fields` - Field names to include.
- `flat` - If True, return single values instead of tuples (only valid with one field).
- `named` - If True, return namedtuples.

**Returns:** ValuesListQuerySet yielding tuples or values

## Supported Relation Types

The QuerySet supports these Django relation types:

### ManyToManyField

```python
class Book(models.Model):
    authors = models.ManyToManyField(Author)

Book.objects.prefetch_related("authors").values()
```

### Reverse ForeignKey (ManyToOneRel)

```python
class Chapter(models.Model):
    book = models.ForeignKey(Book, related_name="chapters")

Book.objects.prefetch_related("chapters").values()
```

### Reverse ManyToMany (ManyToManyRel)

```python
# From the "other side" of a M2M
Author.objects.prefetch_related("books").values()
```

### Nested Prefetches

```python
from django.db.models import Prefetch

Publisher.objects.prefetch_related(
    Prefetch(
        "books",
        queryset=Book.objects.prefetch_related("authors")
    )
).values()
```

## Using with Prefetch Objects

Django's `Prefetch` object is fully supported:

### Filtering Prefetched Data

```python
Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.filter(active=True))
).values()
```

### Custom to_attr

```python
Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.all(), to_attr="author_list")
).values()
# [{"id": 1, "title": "...", "author_list": [...]}, ...]
```

### Nested Prefetch with values()

```python
Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.values("id", "name"))
).values()
```

## Query Efficiency

`PrefetchValuesQuerySet` uses the same number of queries as standard Django prefetching - one query for the main model plus one query per prefetch relation.

```python
# 2 queries total: 1 for books, 1 for authors
Book.objects.prefetch_related("authors").values()

# 3 queries total: 1 for publishers, 1 for books, 1 for authors
Publisher.objects.prefetch_related(
    Prefetch("books", queryset=Book.objects.prefetch_related("authors"))
).values()
```

The performance benefit comes from avoiding Django model instantiation, not from reducing the number of queries.
