# django-prefetch-values

Enable `.prefetch_related().values()` in Django ORM - returns nested dicts with prefetched relations.

This package solves [Django ticket #26565](https://code.djangoproject.com/ticket/26565), which has been open since 2016.

## Installation

```bash
pip install django-prefetch-values
```

## Usage

### Basic Usage

Use `PrefetchValuesQuerySet` as a custom manager for your models:

```python
from django.db import models
from django_prefetch_values import PrefetchValuesQuerySet


class BookManager(models.Manager.from_queryset(PrefetchValuesQuerySet)):
    pass


class Book(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField("Author", related_name="books")
    publisher = models.ForeignKey("Publisher", on_delete=models.CASCADE)

    objects = BookManager()
```

Now you can use `prefetch_related()` with `values()`:

```python
# Get books with nested author data as dicts
books = Book.objects.prefetch_related("authors").values("title", "authors")
# Returns:
# [
#     {
#         "title": "Django for Beginners",
#         "authors": [
#             {"id": 1, "name": "John Doe", "email": "john@example.com"},
#             {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
#         ]
#     },
#     ...
# ]
```

### Supported Relation Types

- **ManyToMany**: Returns a list of dicts
- **Reverse ForeignKey** (one-to-many): Returns a list of dicts
- **ForeignKey** (many-to-one): Returns a single dict (or None)

```python
# ManyToMany
Book.objects.prefetch_related("authors").values("title", "authors")

# Reverse ForeignKey (chapters belong to book)
Book.objects.prefetch_related("chapters").values("title", "chapters")

# ForeignKey (publisher is a single object)
Book.objects.prefetch_related("publisher").values("title", "publisher")
# Returns: {"title": "...", "publisher": {"id": 1, "name": "...", "country": "..."}}
```

### Selecting Specific Fields

You can select specific fields from prefetched relations using double-underscore notation:

```python
# Only get author names, not emails
Book.objects.prefetch_related("authors").values("title", "authors__name")
# Returns: [{"title": "...", "authors": [{"name": "John Doe"}, ...]}]
```

### Nested Prefetching

Nested relations are supported:

```python
# Get authors with their books and each book's chapters
Author.objects.prefetch_related("books__chapters").values("name", "books")
# Returns:
# [
#     {
#         "name": "John Doe",
#         "books": [
#             {
#                 "id": 1,
#                 "title": "Django for Beginners",
#                 "chapters": [
#                     {"id": 1, "title": "Introduction", "number": 1},
#                     {"id": 2, "title": "Models", "number": 2},
#                 ]
#             },
#             ...
#         ]
#     },
#     ...
# ]
```

### Using Prefetch Objects

Custom `Prefetch` objects with querysets and `to_attr` are supported:

```python
from django.db.models import Prefetch

# Only prefetch chapters with page_count > 30
prefetch = Prefetch(
    "chapters",
    queryset=Chapter.objects.filter(page_count__gt=30)
)
Book.objects.prefetch_related(prefetch).values("title", "chapters")

# Using to_attr
prefetch = Prefetch(
    "chapters",
    queryset=Chapter.objects.filter(number=1),
    to_attr="first_chapter"
)
Book.objects.prefetch_related(prefetch).values("title", "first_chapter")
```

### Query Efficiency

This package maintains the query efficiency of `prefetch_related()`. The number of queries equals:
- 1 query for the main model
- 1 query per prefetched relation

```python
# 2 queries total: books + authors
Book.objects.prefetch_related("authors").values("title", "authors")

# 4 queries total: books + authors + tags + chapters
Book.objects.prefetch_related("authors", "tags", "chapters").values(
    "title", "authors", "tags", "chapters"
)
```

## Benchmarks

Benchmark fetching 1,000 books with 5 relations each (publisher, authors, tags, chapters, reviews):

| Method | Mean Time | Queries | Notes |
|--------|-----------|---------|-------|
| Normal prefetch + manual dict | 130.38ms | 6 | Standard approach |
| **prefetch_related().values()** | **28.17ms** | **7** | **~4.6x faster** |
| Standard values() | 3.67ms | 1 | Loses M2M/reverse FK data |

**Test data:**
- 1,000 books
- ~3,000 chapters (1-5 per book)
- ~1,500 reviews (0-3 per book)
- 200 authors (1-3 per book)
- 30 tags (1-4 per book)
- 50 publishers

Our implementation is **~4.6x faster** than manually converting prefetched model instances to dicts. The speedup comes from using `.values()` queries directly instead of hydrating full Django model instances - we never create model objects, only lightweight dictionaries.

Run the benchmark yourself:
```bash
python benchmarks/benchmark.py
```

## How It Works

The package intercepts `.values()` calls when `prefetch_related()` has been used. Instead of executing the normal values query (which would lose the prefetch), it:

1. Executes the main query using `.values()` to get only the requested fields
2. For each prefetched relation, executes a separate `.values()` query to fetch related data
3. Joins the results in Python by matching primary keys
4. Returns nested dictionaries without ever creating Django model instances

## Requirements

- Python >= 3.13
- Django >= 6.0

## License

MIT
